import {
  ANALYSIS_TIMEOUT_MS,
  createAnchorTimes,
  createRefinementTimes,
  decideAnalysis,
  MAX_TOTAL_SAMPLES,
  RISK_THRESHOLD,
} from './sampling'
import {
  AnalysisCancelledError,
  type AnalysisController,
  type AnalysisProgress,
  type AnalysisResult,
  AnalysisSetupError,
  type ModelMode,
} from './types'
import type { AnalysisWorkerEvent, WorkerCommand } from './worker-protocol'

interface WorkerModelInfo {
  modelMode: ModelMode
  modelLabel: string
}

interface PendingRequest<T> {
  resolve: (value: T) => void
  reject: (reason: Error) => void
}

function identifier(): string {
  return typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : `${String(Date.now())}-${Math.random().toString(16).slice(2)}`
}

function asError(error: unknown): Error {
  return error instanceof Error ? error : new Error('Analysis failed')
}

class WorkerClient {
  private initialization: PendingRequest<WorkerModelInfo> | undefined
  private classification: PendingRequest<number> | undefined
  private activeRequestId: string | undefined
  private disposed = false
  private readonly worker: Worker
  private readonly scanId: string

  constructor(worker: Worker, scanId: string) {
    this.worker = worker
    this.scanId = scanId
    worker.addEventListener('message', this.onMessage)
    worker.addEventListener('error', this.onWorkerError)
  }

  initialize(): Promise<WorkerModelInfo> {
    return new Promise((resolve, reject) => {
      this.initialization = { resolve, reject }
      this.post({ type: 'initialize', scanId: this.scanId })
    })
  }

  classify(bitmap: ImageBitmap): Promise<number> {
    if (this.classification !== undefined) {
      bitmap.close()
      return Promise.reject(
        new Error('Only one classification may be in flight'),
      )
    }

    const requestId = identifier()
    this.activeRequestId = requestId
    return new Promise((resolve, reject) => {
      this.classification = { resolve, reject }
      this.worker.postMessage(
        { type: 'classify', scanId: this.scanId, requestId, bitmap },
        [bitmap],
      )
    })
  }

  cancel(): void {
    if (!this.disposed) this.post({ type: 'cancel', scanId: this.scanId })
    this.rejectPending(new AnalysisCancelledError())
  }

  dispose(): void {
    if (this.disposed) return
    this.disposed = true
    this.post({ type: 'dispose', scanId: this.scanId })
    this.rejectPending(new AnalysisCancelledError())
    this.worker.removeEventListener('message', this.onMessage)
    this.worker.removeEventListener('error', this.onWorkerError)
    this.worker.terminate()
  }

  private readonly onMessage = (message: MessageEvent<AnalysisWorkerEvent>) => {
    const event = message.data
    if (event.scanId !== this.scanId) return

    if (event.type === 'initialized') {
      this.initialization?.resolve({
        modelMode: event.modelMode,
        modelLabel: event.modelLabel,
      })
      this.initialization = undefined
      return
    }

    if (
      event.type === 'classified' &&
      event.requestId === this.activeRequestId
    ) {
      this.classification?.resolve(event.risk)
      this.classification = undefined
      this.activeRequestId = undefined
      return
    }

    if (event.type === 'error') {
      const error = new AnalysisSetupError(event.message)
      if (event.requestId === undefined) {
        this.initialization?.reject(error)
        this.initialization = undefined
      } else if (event.requestId === this.activeRequestId) {
        this.classification?.reject(error)
        this.classification = undefined
        this.activeRequestId = undefined
      }
    }
  }

  private readonly onWorkerError = () => {
    this.rejectPending(
      new AnalysisSetupError('The model worker stopped unexpectedly'),
    )
  }

  private post(command: WorkerCommand): void {
    this.worker.postMessage(command)
  }

  private rejectPending(error: Error): void {
    this.initialization?.reject(error)
    this.classification?.reject(error)
    this.initialization = undefined
    this.classification = undefined
    this.activeRequestId = undefined
  }
}

class ProgressReporter {
  private lastProgress: AnalysisProgress | undefined
  private lastReportedAt = 0
  private timer: ReturnType<typeof setTimeout> | undefined
  private readonly callback: (progress: AnalysisProgress) => void

  constructor(callback: (progress: AnalysisProgress) => void) {
    this.callback = callback
  }

  report(progress: AnalysisProgress, immediate = false): void {
    this.lastProgress = progress
    const now = performance.now()
    if (immediate || now - this.lastReportedAt >= 100) {
      this.flush()
      return
    }

    this.timer ??= setTimeout(
      () => {
        this.timer = undefined
        this.flush()
      },
      100 - (now - this.lastReportedAt),
    )
  }

  dispose(): void {
    if (this.timer !== undefined) clearTimeout(this.timer)
    this.timer = undefined
    this.lastProgress = undefined
  }

  private flush(): void {
    if (this.lastProgress === undefined) return
    if (this.timer !== undefined) clearTimeout(this.timer)
    this.timer = undefined
    this.lastReportedAt = performance.now()
    this.callback(this.lastProgress)
    this.lastProgress = undefined
  }
}

function waitForVideoEvent(
  video: HTMLVideoElement,
  successEvent: 'loadeddata' | 'seeked',
  signal: AbortSignal,
): Promise<void> {
  if (signal.aborted) return Promise.reject(new AnalysisCancelledError())

  return new Promise((resolve, reject) => {
    const cleanup = () => {
      video.removeEventListener(successEvent, onSuccess)
      video.removeEventListener('error', onError)
      signal.removeEventListener('abort', onAbort)
    }
    const onSuccess = () => {
      cleanup()
      resolve()
    }
    const onError = () => {
      cleanup()
      reject(new AnalysisSetupError('The selected video could not be decoded'))
    }
    const onAbort = () => {
      cleanup()
      reject(new AnalysisCancelledError())
    }

    video.addEventListener(successEvent, onSuccess, { once: true })
    video.addEventListener('error', onError, { once: true })
    signal.addEventListener('abort', onAbort, { once: true })
  })
}

async function loadVideo(
  video: HTMLVideoElement,
  sourceUrl: string,
  signal: AbortSignal,
): Promise<number> {
  video.preload = 'auto'
  video.muted = true
  video.playsInline = true
  video.src = sourceUrl
  video.load()
  await waitForVideoEvent(video, 'loadeddata', signal)

  if (video.duration === Number.POSITIVE_INFINITY) {
    const durationResolved = waitForVideoEvent(video, 'seeked', signal)
    video.currentTime = Number.MAX_SAFE_INTEGER
    await durationResolved
    const returnToStart = waitForVideoEvent(video, 'seeked', signal)
    video.currentTime = 0
    await returnToStart
  }

  if (!Number.isFinite(video.duration) || video.duration <= 0) {
    throw new AnalysisSetupError('The selected video has no usable duration')
  }
  return video.duration
}

async function seekVideo(
  video: HTMLVideoElement,
  seconds: number,
  signal: AbortSignal,
): Promise<void> {
  if (Math.abs(video.currentTime - seconds) < 0.01) return
  const ready = waitForVideoEvent(video, 'seeked', signal)
  video.currentTime = seconds
  await ready
}

function progress(
  phase: AnalysisProgress['phase'],
  completedSamples: number,
  plannedSamples: number,
): AnalysisProgress {
  const percent =
    plannedSamples === 0
      ? 0
      : Math.min(100, Math.round((completedSamples / plannedSamples) * 100))
  return { phase, completedSamples, plannedSamples, percent }
}

interface SampleTarget {
  seconds: number
  kind: 'anchor' | 'refinement'
}

export interface BrowserAnalysisDependencies {
  createWorker: () => Worker
  createVideo: () => HTMLVideoElement
  createBitmap: (video: HTMLVideoElement) => Promise<ImageBitmap>
  createObjectUrl: (file: File) => string
  revokeObjectUrl: (url: string) => void
  now: () => number
}

const browserDependencies: BrowserAnalysisDependencies = {
  createWorker: () =>
    new Worker(new URL('./worker/analysis.worker.ts', import.meta.url), {
      type: 'module',
      name: 'bbcds-analysis',
    }),
  createVideo: () => document.createElement('video'),
  createBitmap: (video) => createImageBitmap(video),
  createObjectUrl: (file) => URL.createObjectURL(file),
  revokeObjectUrl: (url) => {
    URL.revokeObjectURL(url)
  },
  now: () => performance.now(),
}

export class BrowserAnalysisController implements AnalysisController {
  private readonly dependencies: BrowserAnalysisDependencies

  constructor(dependencies: BrowserAnalysisDependencies = browserDependencies) {
    this.dependencies = dependencies
  }

  async analyze(
    file: File,
    callbacks: { onProgress: (value: AnalysisProgress) => void },
    signal: AbortSignal,
  ): Promise<AnalysisResult> {
    const scanId = identifier()
    const worker = this.dependencies.createWorker()
    const client = new WorkerClient(worker, scanId)
    const video = this.dependencies.createVideo()
    const sourceUrl = this.dependencies.createObjectUrl(file)
    const reporter = new ProgressReporter(callbacks.onProgress)
    const startedAt = this.dependencies.now()
    const cancelWorker = () => {
      client.cancel()
    }
    signal.addEventListener('abort', cancelWorker, { once: true })

    try {
      reporter.report(progress('preparing', 0, 0), true)
      const durationSeconds = await loadVideo(video, sourceUrl, signal)
      const anchors = createAnchorTimes(durationSeconds)
      const queue: SampleTarget[] = anchors.map((seconds) => ({
        seconds,
        kind: 'anchor',
      }))
      const existingTimes = [...anchors]
      const refinedAnchors = new Set<number>()
      const risks: number[] = []
      let completedSamples = 0

      reporter.report(progress('loading-model', 0, anchors.length), true)
      const model = await client.initialize()
      reporter.report(progress('scanning', 0, anchors.length), true)

      for (let index = 0; index < queue.length; index += 1) {
        if (signal.aborted) throw new AnalysisCancelledError()
        if (this.dependencies.now() - startedAt >= ANALYSIS_TIMEOUT_MS) {
          const timedOut = decideAnalysis({
            modelMode: model.modelMode,
            risks,
            anchorsComplete: false,
            timedOut: true,
          })
          if (timedOut === null) {
            throw new AnalysisSetupError(
              'Timed-out analysis produced no result',
            )
          }
          return {
            ...timedOut,
            modelMode: model.modelMode,
            modelLabel: model.modelLabel,
            completedSamples,
            plannedSamples: queue.length,
            durationSeconds,
          }
        }

        const target = queue[index]
        if (target === undefined) {
          throw new AnalysisSetupError('The sampling plan became invalid')
        }
        reporter.report(
          progress(
            target.kind === 'anchor' ? 'scanning' : 'refining',
            completedSamples,
            queue.length,
          ),
          target.kind === 'refinement',
        )
        await seekVideo(video, target.seconds, signal)
        const bitmap = await this.dependencies.createBitmap(video)
        const risk = await client.classify(bitmap)
        risks.push(risk)
        completedSamples += 1

        if (
          model.modelMode === 'approved' &&
          target.kind === 'anchor' &&
          risk >= RISK_THRESHOLD &&
          !refinedAnchors.has(target.seconds) &&
          queue.length < MAX_TOTAL_SAMPLES
        ) {
          refinedAnchors.add(target.seconds)
          const refinements = createRefinementTimes(
            target.seconds,
            durationSeconds,
            existingTimes,
          ).map((seconds) => ({ seconds, kind: 'refinement' as const }))
          existingTimes.push(...refinements.map(({ seconds }) => seconds))
          queue.splice(index + 1, 0, ...refinements)
        }

        const earlyDecision = decideAnalysis({
          modelMode: model.modelMode,
          risks,
          anchorsComplete: false,
          timedOut: false,
        })
        if (earlyDecision?.decision === 'sensitive') {
          reporter.report(
            progress('refining', completedSamples, queue.length),
            true,
          )
          return {
            ...earlyDecision,
            modelMode: model.modelMode,
            modelLabel: model.modelLabel,
            completedSamples,
            plannedSamples: queue.length,
            durationSeconds,
          }
        }
      }

      const decision = decideAnalysis({
        modelMode: model.modelMode,
        risks,
        anchorsComplete: true,
        timedOut: false,
      })
      if (decision === null) {
        throw new AnalysisSetupError('Completed analysis produced no result')
      }
      reporter.report(
        progress('scanning', completedSamples, queue.length),
        true,
      )
      return {
        ...decision,
        modelMode: model.modelMode,
        modelLabel: model.modelLabel,
        completedSamples,
        plannedSamples: queue.length,
        durationSeconds,
      }
    } catch (error) {
      if (signal.aborted || error instanceof AnalysisCancelledError) {
        throw new AnalysisCancelledError()
      }
      throw asError(error)
    } finally {
      signal.removeEventListener('abort', cancelWorker)
      reporter.dispose()
      client.dispose()
      video.pause()
      video.removeAttribute('src')
      video.load()
      this.dependencies.revokeObjectUrl(sourceUrl)
    }
  }
}

export function createAnalysisController(): AnalysisController {
  return new BrowserAnalysisController()
}
