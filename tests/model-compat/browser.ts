import {
  Tensor,
  loadAndCompile,
  loadLiteRt,
  unloadLiteRt,
} from '@litertjs/core'

import {
  runCompatibility,
  type CompatibilityPolicy,
  type RuntimeAdapter,
} from './harness'

const adapter: RuntimeAdapter = {
  initialize: async () => loadLiteRt('/litert-wasm/').then(() => undefined),
  compile: async () => {
    const model = await loadAndCompile('/protected-model.tflite', {
      accelerator: 'wasm',
    })
    return {
      getInputDetails: () => model.getInputDetails(),
      getOutputDetails: () => model.getOutputDetails(),
      run: async (input) => model.run(input as Tensor),
      delete: () => {
        model.delete()
      },
    }
  },
  createTensor: (data, shape) => new Tensor(data, shape),
  unload: () => {
    unloadLiteRt()
  },
}

declare global {
  interface Window {
    __BBCDS_MODEL_COMPATIBILITY__: ReturnType<typeof runCompatibility>
  }
}

window.__BBCDS_MODEL_COMPATIBILITY__ = fetch('/compat-policy.json')
  .then((response) => {
    if (!response.ok)
      throw new Error('Compatibility policy could not be loaded')
    return response.json() as Promise<CompatibilityPolicy>
  })
  .then((policy) => runCompatibility(adapter, policy))
