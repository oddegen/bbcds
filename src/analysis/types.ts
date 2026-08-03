export type ModelMode = 'demo' | 'approved'

export type AnalysisPhase =
  'preparing' | 'loading-model' | 'scanning' | 'refining'

export interface AnalysisProgress {
  phase: AnalysisPhase
  completedSamples: number
  plannedSamples: number
  percent: number
}

export type AnalysisDecision = 'demo' | 'safe' | 'sensitive' | 'inconclusive'

export interface AnalysisResult {
  decision: AnalysisDecision
  modelMode: ModelMode
  modelLabel: string
  confidence?: number
  completedSamples: number
  plannedSamples: number
  durationSeconds: number
  reason?: 'unconfirmed' | 'timeout' | 'cancelled'
}

export interface AnalysisCallbacks {
  onProgress: (progress: AnalysisProgress) => void
}

export interface AnalysisController {
  analyze(
    file: File,
    callbacks: AnalysisCallbacks,
    signal: AbortSignal,
  ): Promise<AnalysisResult>
}

export type AnalysisControllerFactory = () => AnalysisController

export class AnalysisCancelledError extends Error {
  constructor() {
    super('Analysis was cancelled')
    this.name = 'AnalysisCancelledError'
  }
}

export class AnalysisSetupError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'AnalysisSetupError'
  }
}
