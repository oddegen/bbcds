import { describe, expect, it } from 'vitest'

import {
  runCompatibility,
  type CompiledModelHandle,
  type RuntimeAdapter,
  type TensorHandle,
} from './harness'

const policy = {
  inputShape: [1, 224, 224, 3],
  outputShape: [1, 4],
  inputDType: 'float32',
  outputDType: 'float32',
  warmupIterations: 10,
  measuredIterations: 50,
}

class FakeTensor implements TensorHandle {
  deleted = false
  private readonly values: number[]

  constructor(values: number[]) {
    this.values = values
  }

  toTypedArray() {
    return this.values
  }

  delete() {
    this.deleted = true
  }
}

function fakeRuntime(options: { validOutput?: boolean } = {}) {
  const inputs: FakeTensor[] = []
  const outputs: FakeTensor[] = []
  let modelDeleted = false
  let runtimeUnloaded = false
  const model: CompiledModelHandle = {
    getInputDetails: () => [{ dtype: 'float32', shape: [1, 224, 224, 3] }],
    getOutputDetails: () => [{ dtype: 'float32', shape: [1, 4] }],
    run: () => {
      const output = new FakeTensor(
        options.validOutput === false ? [1, 1, 1, 1] : [0.25, 0.25, 0.25, 0.25],
      )
      outputs.push(output)
      return Promise.resolve([output])
    },
    delete: () => {
      modelDeleted = true
    },
  }
  const adapter: RuntimeAdapter = {
    initialize: () => Promise.resolve(),
    compile: () => Promise.resolve(model),
    createTensor: () => {
      const input = new FakeTensor([])
      inputs.push(input)
      return input
    },
    unload: () => {
      runtimeUnloaded = true
    },
  }
  return {
    adapter,
    inputs,
    outputs,
    cleaned: () => modelDeleted && runtimeUnloaded,
  }
}

describe('protected model compatibility harness', () => {
  it('records aggregate timings and releases every runtime object', async () => {
    const runtime = fakeRuntime()
    let clock = 0
    const result = await runCompatibility(
      runtime.adapter,
      policy,
      () => ++clock,
    )

    expect(result.compatibility.passed).toBe(true)
    expect(result.benchmark.measuredIterations).toBe(50)
    expect(runtime.inputs).toHaveLength(60)
    expect(runtime.inputs.every((tensor) => tensor.deleted)).toBe(true)
    expect(runtime.outputs.every((tensor) => tensor.deleted)).toBe(true)
    expect(runtime.cleaned()).toBe(true)
  })

  it('rejects invalid probability output and still cleans up', async () => {
    const runtime = fakeRuntime({ validOutput: false })
    await expect(runCompatibility(runtime.adapter, policy)).rejects.toThrow(
      /probability contract/,
    )
    expect(runtime.cleaned()).toBe(true)
    expect(runtime.inputs.every((tensor) => tensor.deleted)).toBe(true)
    expect(runtime.outputs.every((tensor) => tensor.deleted)).toBe(true)
  })
})
