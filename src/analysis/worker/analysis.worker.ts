import type { AnalysisWorkerEvent, WorkerCommand } from '../worker-protocol'
import { createWorkerHandler } from './handler'

interface WorkerScope {
  addEventListener(
    type: 'message',
    listener: (event: MessageEvent<WorkerCommand>) => void,
  ): void
  postMessage(message: AnalysisWorkerEvent): void
}

const scope = globalThis as unknown as WorkerScope
const handle = createWorkerHandler((event) => {
  scope.postMessage(event)
})

scope.addEventListener('message', (event) => {
  void handle(event.data)
})
