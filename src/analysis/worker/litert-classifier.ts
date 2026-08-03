import type { CompiledModel, Tensor } from '@litertjs/core'

import type { FrameClassifier } from './classifier'
import { DemoClassifier } from './demo-classifier'

const MANIFEST_URL = '/models/model-manifest-approved.json'
const WASM_URL = '/litert-wasm/'
const INPUT_SHAPE = [1, 224, 224, 3] as const
const OUTPUT_SHAPE = [1, 4] as const
const LABELS = [
  'Safe',
  'Suggestive',
  'Explicit',
  'Explicit Illustration',
] as const
const SAFE_IDENTIFIER = /^[A-Za-z0-9._-]+$/
const SEMANTIC_VERSION = /^\d+\.\d+\.\d+$/

interface ApprovedManifest {
  modelId: string
  semanticVersion: string
  artifact: { sha256: string; sizeBytes: number }
}

type Fetcher = typeof fetch

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function equalArray(value: unknown, expected: readonly unknown[]): boolean {
  return (
    Array.isArray(value) &&
    value.length === expected.length &&
    value.every((item, index) => item === expected[index])
  )
}

function approvedManifest(value: unknown): ApprovedManifest {
  if (!isRecord(value)) throw new Error('Model manifest must be an object')

  const artifact = value.artifact
  const input = value.input
  const output = value.output
  const runtime = value.runtime
  const approval = value.approval
  const modelId = value.modelId
  const semanticVersion = value.semanticVersion

  if (
    value.schemaVersion !== 1 ||
    typeof modelId !== 'string' ||
    !SAFE_IDENTIFIER.test(modelId) ||
    typeof semanticVersion !== 'string' ||
    !SEMANTIC_VERSION.test(semanticVersion) ||
    !isRecord(artifact) ||
    typeof artifact.sha256 !== 'string' ||
    !/^[a-f0-9]{64}$/.test(artifact.sha256) ||
    !Number.isSafeInteger(artifact.sizeBytes) ||
    (artifact.sizeBytes as number) <= 0 ||
    !equalArray(value.labels, LABELS) ||
    !isRecord(input) ||
    !equalArray(input.shape, INPUT_SHAPE) ||
    input.dtype !== 'float32' ||
    !equalArray(input.range, [0, 255]) ||
    input.colorSpace !== 'RGB' ||
    input.layout !== 'NHWC' ||
    input.resize !== 'aspect-preserving-letterbox' ||
    input.modelPreprocessing !== 'MobileNetV3' ||
    !isRecord(output) ||
    !equalArray(output.shape, OUTPUT_SHAPE) ||
    output.dtype !== 'float32' ||
    output.semantics !== 'probabilities' ||
    !isRecord(runtime) ||
    runtime.package !== '@litertjs/core' ||
    runtime.accelerator !== 'wasm' ||
    !isRecord(approval) ||
    approval.status !== 'approved'
  ) {
    throw new Error(
      'Model manifest does not match the approved browser contract',
    )
  }

  return {
    modelId,
    semanticVersion,
    artifact: {
      sha256: artifact.sha256,
      sizeBytes: artifact.sizeBytes as number,
    },
  }
}

function hexDigest(buffer: ArrayBuffer): Promise<string> {
  return crypto.subtle
    .digest('SHA-256', buffer)
    .then((digest) =>
      Array.from(new Uint8Array(digest), (byte) =>
        byte.toString(16).padStart(2, '0'),
      ).join(''),
    )
}

function equalShape(actual: ArrayLike<number>, expected: readonly number[]) {
  return (
    actual.length === expected.length &&
    Array.from(actual).every((value, index) => value === expected[index])
  )
}

function validateTensorContract(model: CompiledModel): void {
  const inputs = model.getInputDetails()
  const outputs = model.getOutputDetails()
  const input = inputs[0]
  const output = outputs[0]

  if (
    inputs.length !== 1 ||
    outputs.length !== 1 ||
    input === undefined ||
    output === undefined ||
    input.dtype !== 'float32' ||
    output.dtype !== 'float32' ||
    !equalShape(input.shape, INPUT_SHAPE) ||
    !equalShape(output.shape, OUTPUT_SHAPE)
  ) {
    throw new Error('Model tensor contract is incompatible with BBCDS')
  }
}

function imageTensor(bitmap: ImageBitmap): Float32Array {
  if (typeof OffscreenCanvas === 'undefined') {
    throw new Error('This browser cannot preprocess frames in a worker')
  }

  const canvas = new OffscreenCanvas(INPUT_SHAPE[2], INPUT_SHAPE[1])
  const context = canvas.getContext('2d', { willReadFrequently: true })
  if (context === null) throw new Error('Worker canvas is unavailable')

  const scale = Math.min(
    INPUT_SHAPE[2] / bitmap.width,
    INPUT_SHAPE[1] / bitmap.height,
  )
  const width = bitmap.width * scale
  const height = bitmap.height * scale
  const left = (INPUT_SHAPE[2] - width) / 2
  const top = (INPUT_SHAPE[1] - height) / 2

  context.fillStyle = '#000000'
  context.fillRect(0, 0, INPUT_SHAPE[2], INPUT_SHAPE[1])
  context.drawImage(bitmap, left, top, width, height)
  const rgba = context.getImageData(0, 0, INPUT_SHAPE[2], INPUT_SHAPE[1]).data
  const rgb = new Float32Array(INPUT_SHAPE[1] * INPUT_SHAPE[2] * 3)

  for (let source = 0, target = 0; source < rgba.length; source += 4) {
    rgb[target] = rgba[source] ?? 0
    rgb[target + 1] = rgba[source + 1] ?? 0
    rgb[target + 2] = rgba[source + 2] ?? 0
    target += 3
  }

  return rgb
}

function frameRisk(probabilities: ArrayLike<number>): number {
  const values = Array.from(probabilities)
  const suggestive = values[1]
  const explicit = values[2]
  const illustration = values[3]
  const sum = values.reduce((total, value) => total + value, 0)
  if (
    values.length !== OUTPUT_SHAPE[1] ||
    suggestive === undefined ||
    explicit === undefined ||
    illustration === undefined ||
    values.some((value) => !Number.isFinite(value) || value < 0 || value > 1) ||
    Math.abs(sum - 1) > 0.01
  ) {
    throw new Error('Model output does not satisfy the probability contract')
  }

  return Math.min(1, explicit + illustration + 0.35 * suggestive)
}

export class LiteRtClassifier implements FrameClassifier {
  readonly info
  private readonly model: CompiledModel
  private readonly TensorConstructor: typeof Tensor
  private readonly unload: () => void

  private constructor(
    model: CompiledModel,
    TensorConstructor: typeof Tensor,
    unload: () => void,
    modelId: string,
    semanticVersion: string,
  ) {
    this.model = model
    this.TensorConstructor = TensorConstructor
    this.unload = unload
    this.info = {
      modelMode: 'approved' as const,
      modelLabel: `${modelId} ${semanticVersion}`,
    }
  }

  static async create(
    manifest: ApprovedManifest,
    modelBytes: Uint8Array,
  ): Promise<LiteRtClassifier> {
    const runtime = await import('@litertjs/core')
    await runtime.loadLiteRt(WASM_URL)

    try {
      const model = await runtime.loadAndCompile(modelBytes, {
        accelerator: 'wasm',
      })
      try {
        validateTensorContract(model)
      } catch (error) {
        model.delete()
        throw error
      }
      return new LiteRtClassifier(
        model,
        runtime.Tensor,
        runtime.unloadLiteRt,
        manifest.modelId,
        manifest.semanticVersion,
      )
    } catch (error) {
      runtime.unloadLiteRt()
      throw error
    }
  }

  async classify(bitmap: ImageBitmap): Promise<number> {
    let input: Tensor | undefined
    let outputs: Tensor[] = []
    try {
      const values = imageTensor(bitmap)
      input = new this.TensorConstructor(values, [...INPUT_SHAPE])
      outputs = await this.model.run(input)
      const output = outputs[0]
      if (outputs.length !== 1 || output === undefined) {
        throw new Error('Model must return exactly one output tensor')
      }
      return frameRisk(output.toTypedArray())
    } finally {
      bitmap.close()
      for (const output of outputs) output.delete()
      input?.delete()
    }
  }

  dispose(): void {
    this.model.delete()
    this.unload()
  }
}

export async function loadClassifier(
  fetcher: Fetcher = fetch,
): Promise<FrameClassifier> {
  const manifestResponse = await fetcher(MANIFEST_URL, { cache: 'no-store' })
  const contentType = manifestResponse.headers.get('content-type') ?? ''
  if (
    manifestResponse.status === 404 ||
    (manifestResponse.ok && contentType.includes('text/html'))
  ) {
    return new DemoClassifier()
  }
  if (!manifestResponse.ok) {
    throw new Error('Approved model manifest could not be loaded')
  }

  const manifest = approvedManifest(await manifestResponse.json())
  const artifactUrl = `/models/${manifest.modelId}-${manifest.semanticVersion}.tflite`
  const artifactResponse = await fetcher(artifactUrl, { cache: 'no-store' })
  if (!artifactResponse.ok)
    throw new Error('Approved model artifact is missing')

  const buffer = await artifactResponse.arrayBuffer()
  if (buffer.byteLength !== manifest.artifact.sizeBytes) {
    throw new Error('Model artifact size does not match its approved manifest')
  }
  if ((await hexDigest(buffer)) !== manifest.artifact.sha256) {
    throw new Error('Model artifact hash does not match its approved manifest')
  }

  return LiteRtClassifier.create(manifest, new Uint8Array(buffer))
}
