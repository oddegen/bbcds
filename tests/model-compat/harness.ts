export interface TensorDetails {
  dtype: string
  shape: ArrayLike<number>
}

export interface TensorHandle {
  toTypedArray(): ArrayLike<number>
  delete(): void
}

export interface CompiledModelHandle {
  getInputDetails(): readonly TensorDetails[]
  getOutputDetails(): readonly TensorDetails[]
  run(input: TensorHandle): Promise<TensorHandle[]>
  delete(): void
}

export interface RuntimeAdapter {
  initialize(): Promise<void>
  compile(): Promise<CompiledModelHandle>
  createTensor(data: Float32Array, shape: number[]): TensorHandle
  unload(): void
}

export interface CompatibilityPolicy {
  inputShape: number[]
  outputShape: number[]
  inputDType: string
  outputDType: string
  warmupIterations: number
  measuredIterations: number
}

export interface CompatibilityResult {
  tensorContract: {
    inputShape: number[]
    inputDType: string
    outputShape: number[]
    outputDType: string
  }
  benchmark: {
    runtimeInitializationMs: number
    modelCompilationMs: number
    warmupIterations: number
    measuredIterations: number
    inferenceMs: {
      minimum: number
      p50: number
      p95: number
      maximum: number
    }
  }
  compatibility: {
    runtimeInitialized: boolean
    modelCompiled: boolean
    inferenceCompleted: boolean
    resourcesReleased: boolean
    passed: boolean
  }
}

function elapsed(start: number, end: number): number {
  return Math.max(0, end - start)
}

function percentile(sorted: number[], fraction: number): number {
  const value = sorted[Math.ceil(fraction * sorted.length) - 1]
  if (value === undefined) throw new Error('Inference timings are empty')
  return value
}

function equalShape(actual: ArrayLike<number>, expected: number[]): boolean {
  return (
    actual.length === expected.length &&
    Array.from(actual).every((value, index) => value === expected[index])
  )
}

function validateProbabilityOutput(
  values: ArrayLike<number>,
  outputShape: number[],
): void {
  const probabilities = Array.from(values)
  const sum = probabilities.reduce((total, value) => total + value, 0)
  if (
    probabilities.length !== outputShape.at(-1) ||
    probabilities.some(
      (value) => !Number.isFinite(value) || value < -1e-6 || value > 1 + 1e-6,
    ) ||
    Math.abs(sum - 1) > 0.01
  ) {
    throw new Error('LiteRT output does not satisfy the probability contract')
  }
}

function syntheticInput(inputShape: number[]): Float32Array {
  const values = new Float32Array(
    inputShape.reduce((total, value) => total * value, 1),
  )
  for (let index = 0; index < values.length; index += 1) {
    values[index] = (index * 17 + 31) % 256
  }
  return values
}

async function runOnce(
  adapter: RuntimeAdapter,
  model: CompiledModelHandle,
  values: Float32Array,
  inputShape: number[],
  now: () => number,
): Promise<{ duration: number; output: number[] }> {
  const input = adapter.createTensor(values, inputShape)
  let outputs: TensorHandle[] = []
  const start = now()
  try {
    outputs = await model.run(input)
    if (outputs.length !== 1) {
      throw new Error('LiteRT model must return one output tensor')
    }
    const outputTensor = outputs[0]
    if (!outputTensor) throw new Error('LiteRT output tensor is missing')
    const output = Array.from(outputTensor.toTypedArray())
    return { duration: elapsed(start, now()), output }
  } finally {
    for (const output of outputs) output.delete()
    input.delete()
  }
}

export async function runCompatibility(
  adapter: RuntimeAdapter,
  policy: CompatibilityPolicy,
  now: () => number = () => performance.now(),
): Promise<CompatibilityResult> {
  let model: CompiledModelHandle | undefined
  let runtimeInitialized = false
  try {
    const initStart = now()
    await adapter.initialize()
    const runtimeInitializationMs = elapsed(initStart, now())
    runtimeInitialized = true
    const compileStart = now()
    model = await adapter.compile()
    const modelCompilationMs = elapsed(compileStart, now())
    const inputs = model.getInputDetails()
    const outputs = model.getOutputDetails()
    const input = inputs[0]
    const output = outputs[0]
    if (
      !input ||
      !output ||
      inputs.length !== 1 ||
      outputs.length !== 1 ||
      input.dtype !== policy.inputDType ||
      output.dtype !== policy.outputDType ||
      !equalShape(input.shape, policy.inputShape) ||
      !equalShape(output.shape, policy.outputShape)
    ) {
      throw new Error('LiteRT tensor contract is invalid')
    }
    const values = syntheticInput(policy.inputShape)
    for (let index = 0; index < policy.warmupIterations; index += 1) {
      const result = await runOnce(
        adapter,
        model,
        values,
        policy.inputShape,
        now,
      )
      validateProbabilityOutput(result.output, policy.outputShape)
    }
    const timings: number[] = []
    for (let index = 0; index < policy.measuredIterations; index += 1) {
      const result = await runOnce(
        adapter,
        model,
        values,
        policy.inputShape,
        now,
      )
      validateProbabilityOutput(result.output, policy.outputShape)
      timings.push(result.duration)
    }
    timings.sort((left, right) => left - right)
    const minimum = timings[0]
    const maximum = timings.at(-1)
    if (minimum === undefined || maximum === undefined) {
      throw new Error('Inference timings are empty')
    }
    return {
      tensorContract: {
        inputShape: policy.inputShape,
        inputDType: input.dtype,
        outputShape: policy.outputShape,
        outputDType: output.dtype,
      },
      benchmark: {
        runtimeInitializationMs,
        modelCompilationMs,
        warmupIterations: policy.warmupIterations,
        measuredIterations: policy.measuredIterations,
        inferenceMs: {
          minimum,
          p50: percentile(timings, 0.5),
          p95: percentile(timings, 0.95),
          maximum,
        },
      },
      compatibility: {
        runtimeInitialized: true,
        modelCompiled: true,
        inferenceCompleted: true,
        resourcesReleased: true,
        passed: true,
      },
    }
  } finally {
    model?.delete()
    if (runtimeInitialized) adapter.unload()
  }
}
