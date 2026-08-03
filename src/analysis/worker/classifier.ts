import type { ModelMode } from '../types'

export interface ClassifierInfo {
  modelMode: ModelMode
  modelLabel: string
}

export interface FrameClassifier {
  readonly info: ClassifierInfo
  classify(bitmap: ImageBitmap): Promise<number>
  dispose(): void
}
