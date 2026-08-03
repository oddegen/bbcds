import { vi } from 'vitest'

import type { AnalysisWorkerEvent } from '../worker-protocol'
import type { FrameClassifier } from './classifier'
import { DemoClassifier } from './demo-classifier'
import { createWorkerHandler } from './handler'
import { loadClassifier } from './litert-classifier'

function bitmap(): ImageBitmap {
  return { close: vi.fn() } as unknown as ImageBitmap
}

describe('analysis worker handler', () => {
  it('initializes and classifies with matching scan and request identifiers', async () => {
    const events: AnalysisWorkerEvent[] = []
    const frame = bitmap()
    const classify = vi.fn(() => Promise.resolve(0.7))
    const classifier: FrameClassifier = {
      info: { modelMode: 'approved', modelLabel: 'test-model 1.0.0' },
      classify,
      dispose: vi.fn(),
    }
    const handle = createWorkerHandler(
      (event) => events.push(event),
      () => Promise.resolve(classifier),
    )

    await handle({ type: 'initialize', scanId: 'scan-1' })
    await handle({
      type: 'classify',
      scanId: 'scan-1',
      requestId: 'request-1',
      bitmap: frame,
    })

    expect(events).toEqual([
      {
        type: 'initialized',
        scanId: 'scan-1',
        modelMode: 'approved',
        modelLabel: 'test-model 1.0.0',
      },
      {
        type: 'classified',
        scanId: 'scan-1',
        requestId: 'request-1',
        risk: 0.7,
      },
    ])
    expect(classify).toHaveBeenCalledWith(frame)
  })

  it('closes frames from stale or cancelled scans and disposes resources', async () => {
    const classifier = new DemoClassifier()
    const dispose = vi.spyOn(classifier, 'dispose')
    const staleClose = vi.fn()
    const cancelledClose = vi.fn()
    const stale = { close: staleClose } as unknown as ImageBitmap
    const cancelled = { close: cancelledClose } as unknown as ImageBitmap
    const handle = createWorkerHandler(
      () => undefined,
      () => Promise.resolve(classifier),
    )

    await handle({ type: 'initialize', scanId: 'active' })
    await handle({
      type: 'classify',
      scanId: 'stale',
      requestId: 'request-1',
      bitmap: stale,
    })
    await handle({ type: 'cancel', scanId: 'active' })
    await handle({
      type: 'classify',
      scanId: 'active',
      requestId: 'request-2',
      bitmap: cancelled,
    })
    await handle({ type: 'dispose', scanId: 'active' })

    expect(staleClose).toHaveBeenCalledOnce()
    expect(cancelledClose).toHaveBeenCalledOnce()
    expect(dispose).toHaveBeenCalledOnce()
  })

  it('uses demo mode only when the approved manifest is absent', async () => {
    const demo = await loadClassifier(
      vi.fn(() => Promise.resolve(new Response(null, { status: 404 }))),
    )
    expect(demo.info.modelMode).toBe('demo')

    await expect(
      loadClassifier(
        vi.fn(() =>
          Promise.resolve(
            new Response(JSON.stringify({ schemaVersion: 1 }), {
              status: 200,
              headers: { 'Content-Type': 'application/json' },
            }),
          ),
        ),
      ),
    ).rejects.toThrow('approved browser contract')
  })

  it('disposes a classifier that finishes loading after cancellation', async () => {
    const dispose = vi.fn()
    const classifier: FrameClassifier = {
      info: { modelMode: 'approved', modelLabel: 'late-model' },
      classify: () => Promise.resolve(0),
      dispose,
    }
    let finishLoading: ((value: FrameClassifier) => void) | undefined
    const loading = new Promise<FrameClassifier>((resolve) => {
      finishLoading = resolve
    })
    const events: AnalysisWorkerEvent[] = []
    const handle = createWorkerHandler(
      (event) => events.push(event),
      () => loading,
    )

    const initialization = handle({ type: 'initialize', scanId: 'late-scan' })
    await handle({ type: 'cancel', scanId: 'late-scan' })
    finishLoading?.(classifier)
    await initialization

    expect(dispose).toHaveBeenCalledOnce()
    expect(events).toEqual([])
  })
})
