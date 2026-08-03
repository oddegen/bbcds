import { vi } from 'vitest'

import {
  BrowserAnalysisController,
  type BrowserAnalysisDependencies,
} from './controller'
import { AnalysisCancelledError } from './types'
import type { AnalysisWorkerEvent, WorkerCommand } from './worker-protocol'

class FakeWorker extends EventTarget {
  readonly commands: WorkerCommand[] = []
  terminated = false
  respondToClassification = true
  private readonly mode: 'demo' | 'approved'
  private readonly risks: number[]

  constructor(mode: 'demo' | 'approved', risks: number[] = [0]) {
    super()
    this.mode = mode
    this.risks = risks
  }

  postMessage(command: WorkerCommand): void {
    this.commands.push(command)
    if (command.type === 'initialize') {
      this.emit({
        type: 'initialized',
        scanId: command.scanId,
        modelMode: this.mode,
        modelLabel:
          this.mode === 'demo' ? 'Demo classifier' : 'test-model 1.0.0',
      })
    }
    if (command.type === 'classify' && this.respondToClassification) {
      command.bitmap.close()
      this.emit({
        type: 'classified',
        scanId: command.scanId,
        requestId: command.requestId,
        risk: this.risks.shift() ?? 0,
      })
    }
  }

  terminate(): void {
    this.terminated = true
  }

  private emit(event: AnalysisWorkerEvent): void {
    queueMicrotask(() => {
      this.dispatchEvent(new MessageEvent('message', { data: event }))
    })
  }
}

class FakeVideo extends EventTarget {
  duration = 20
  muted = false
  playsInline = false
  preload = ''
  src = ''
  paused = false
  sourceRemoved = false
  private time = 0

  get currentTime(): number {
    return this.time
  }

  set currentTime(value: number) {
    this.time = value
    queueMicrotask(() => {
      this.dispatchEvent(new Event('seeked'))
    })
  }

  load(): void {
    if (this.src !== '') {
      queueMicrotask(() => {
        this.dispatchEvent(new Event('loadeddata'))
      })
    }
  }

  pause(): void {
    this.paused = true
  }

  removeAttribute(name: string): void {
    if (name === 'src') {
      this.src = ''
      this.sourceRemoved = true
    }
  }
}

function dependencies(worker: FakeWorker, video: FakeVideo) {
  const revokeObjectUrl = vi.fn()
  const close = vi.fn()
  const values: BrowserAnalysisDependencies = {
    createWorker: () => worker as unknown as Worker,
    createVideo: () => video as unknown as HTMLVideoElement,
    createBitmap: () => Promise.resolve({ close } as unknown as ImageBitmap),
    createObjectUrl: () => 'blob:controller-test',
    revokeObjectUrl,
    now: () => 0,
  }
  return { values, revokeObjectUrl, close }
}

describe('BrowserAnalysisController', () => {
  it('runs complete demo coverage and releases browser resources', async () => {
    const worker = new FakeWorker('demo', [0, 0, 0])
    const video = new FakeVideo()
    const harness = dependencies(worker, video)
    const progress = vi.fn()
    const controller = new BrowserAnalysisController(harness.values)

    const result = await controller.analyze(
      new File(['video'], 'benign.mp4', { type: 'video/mp4' }),
      { onProgress: progress },
      new AbortController().signal,
    )

    expect(result).toMatchObject({
      decision: 'demo',
      completedSamples: 3,
      plannedSamples: 3,
    })
    expect(
      worker.commands.filter(({ type }) => type === 'classify'),
    ).toHaveLength(3)
    expect(worker.terminated).toBe(true)
    expect(video.paused).toBe(true)
    expect(video.sourceRemoved).toBe(true)
    expect(harness.revokeObjectUrl).toHaveBeenCalledWith('blob:controller-test')
    expect(progress).toHaveBeenLastCalledWith(
      expect.objectContaining({ completedSamples: 3, percent: 100 }),
    )
  })

  it('refines an elevated anchor and exits after confirming evidence', async () => {
    const worker = new FakeWorker('approved', [0.5, 0.7])
    const video = new FakeVideo()
    const harness = dependencies(worker, video)
    const controller = new BrowserAnalysisController(harness.values)

    const result = await controller.analyze(
      new File(['video'], 'benign.mp4', { type: 'video/mp4' }),
      { onProgress: () => undefined },
      new AbortController().signal,
    )

    expect(result).toMatchObject({
      decision: 'sensitive',
      completedSamples: 2,
      confidence: 0.6,
    })
    expect(result.plannedSamples).toBeGreaterThan(3)
  })

  it('rejects cancellation and terminates an in-flight worker', async () => {
    const worker = new FakeWorker('demo')
    worker.respondToClassification = false
    const video = new FakeVideo()
    const harness = dependencies(worker, video)
    const controller = new BrowserAnalysisController(harness.values)
    const abortController = new AbortController()

    const pending = controller.analyze(
      new File(['video'], 'benign.mp4', { type: 'video/mp4' }),
      { onProgress: () => undefined },
      abortController.signal,
    )
    await vi.waitFor(() => {
      expect(worker.commands.some(({ type }) => type === 'classify')).toBe(true)
    })
    abortController.abort()

    await expect(pending).rejects.toBeInstanceOf(AnalysisCancelledError)
    expect(worker.commands.some(({ type }) => type === 'cancel')).toBe(true)
    expect(worker.terminated).toBe(true)
    expect(harness.revokeObjectUrl).toHaveBeenCalledOnce()
  })
})
