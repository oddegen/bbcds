import type { ModelMode } from './types'

export interface InitializeCommand {
  type: 'initialize'
  scanId: string
}

export interface ClassifyCommand {
  type: 'classify'
  scanId: string
  requestId: string
  bitmap: ImageBitmap
}

export interface CancelCommand {
  type: 'cancel'
  scanId: string
}

export interface DisposeCommand {
  type: 'dispose'
  scanId: string
}

export type WorkerCommand =
  InitializeCommand | ClassifyCommand | CancelCommand | DisposeCommand

export interface InitializedEvent {
  type: 'initialized'
  scanId: string
  modelMode: ModelMode
  modelLabel: string
}

export interface ClassifiedEvent {
  type: 'classified'
  scanId: string
  requestId: string
  risk: number
}

export interface WorkerErrorEvent {
  type: 'error'
  scanId: string
  requestId?: string
  message: string
}

export interface DisposedEvent {
  type: 'disposed'
  scanId: string
}

export type AnalysisWorkerEvent =
  InitializedEvent | ClassifiedEvent | WorkerErrorEvent | DisposedEvent
