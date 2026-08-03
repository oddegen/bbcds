import type { FrameClassifier } from './classifier'

export class DemoClassifier implements FrameClassifier {
  readonly info = {
    modelMode: 'demo' as const,
    modelLabel: 'Demo classifier — no model installed',
  }

  classify(bitmap: ImageBitmap): Promise<number> {
    bitmap.close()
    return Promise.resolve(0)
  }

  dispose(): void {
    // The demo classifier owns no persistent runtime resources.
  }
}
