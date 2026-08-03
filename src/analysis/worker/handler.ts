import type { AnalysisWorkerEvent, WorkerCommand } from '../worker-protocol'
import type { FrameClassifier } from './classifier'
import { loadClassifier } from './litert-classifier'

type PostEvent = (event: AnalysisWorkerEvent) => void
type ClassifierLoader = () => Promise<FrameClassifier>

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'The model worker failed'
}

export function createWorkerHandler(
  postEvent: PostEvent,
  classifierLoader: ClassifierLoader = loadClassifier,
): (command: WorkerCommand) => Promise<void> {
  let classifier: FrameClassifier | undefined
  let activeScanId: string | undefined
  const cancelledScans = new Set<string>()

  return async (command) => {
    if (command.type === 'cancel') {
      cancelledScans.add(command.scanId)
      return
    }

    if (command.type === 'dispose') {
      cancelledScans.add(command.scanId)
      if (command.scanId === activeScanId) {
        classifier?.dispose()
        classifier = undefined
        activeScanId = undefined
      }
      postEvent({ type: 'disposed', scanId: command.scanId })
      return
    }

    if (command.type === 'initialize') {
      try {
        classifier?.dispose()
        activeScanId = command.scanId
        classifier = await classifierLoader()
        if (cancelledScans.has(command.scanId)) {
          classifier.dispose()
          classifier = undefined
          activeScanId = undefined
          return
        }
        postEvent({
          type: 'initialized',
          scanId: command.scanId,
          ...classifier.info,
        })
      } catch (error) {
        postEvent({
          type: 'error',
          scanId: command.scanId,
          message: errorMessage(error),
        })
      }
      return
    }

    if (
      command.scanId !== activeScanId ||
      cancelledScans.has(command.scanId) ||
      classifier === undefined
    ) {
      command.bitmap.close()
      return
    }

    try {
      const risk = await classifier.classify(command.bitmap)
      if (!cancelledScans.has(command.scanId)) {
        postEvent({
          type: 'classified',
          scanId: command.scanId,
          requestId: command.requestId,
          risk,
        })
      }
    } catch (error) {
      postEvent({
        type: 'error',
        scanId: command.scanId,
        requestId: command.requestId,
        message: errorMessage(error),
      })
    }
  }
}
