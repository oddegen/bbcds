import { useEffect, useId, useRef, useState, type RefObject } from 'react'

import { createAnalysisController } from './analysis/controller'
import {
  AnalysisCancelledError,
  type AnalysisControllerFactory,
  type AnalysisProgress,
  type AnalysisResult,
} from './analysis/types'

type SourceMode = 'file' | 'url'

type ScreenState =
  | { view: 'source'; file: File | null }
  | { view: 'scanning'; file: File; progress: AnalysisProgress }
  | { view: 'result'; file: File; result: AnalysisResult }
  | { view: 'error'; file: File; message: string }

interface MetadataItemProps {
  label: string
  value: string
}

export interface AppProps {
  controllerFactory?: AnalysisControllerFactory
}

const initialProgress: AnalysisProgress = {
  phase: 'preparing',
  completedSamples: 0,
  plannedSamples: 0,
  percent: 0,
}

const bytesFormatter = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 1,
})

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
})

const percentFormatter = new Intl.NumberFormat(undefined, {
  style: 'percent',
  maximumFractionDigits: 0,
})

function formatFileSize(bytes: number) {
  if (bytes === 0) return '0 B'

  const units = ['B', 'KB', 'MB', 'GB'] as const
  const exponent = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  )
  const value = bytes / 1024 ** exponent
  return `${bytesFormatter.format(value)} ${units[exponent] ?? 'GB'}`
}

function cancelledResult(progress: AnalysisProgress): AnalysisResult {
  return {
    decision: 'inconclusive',
    reason: 'cancelled',
    modelMode: 'demo',
    modelLabel: 'Analysis cancelled',
    completedSamples: progress.completedSamples,
    plannedSamples: progress.plannedSamples,
    durationSeconds: 0,
  }
}

function App({ controllerFactory = createAnalysisController }: AppProps) {
  const [screen, setScreen] = useState<ScreenState>({
    view: 'source',
    file: null,
  })
  const activeAbort = useRef<AbortController | null>(null)
  const progressRef = useRef(initialProgress)
  const runId = useRef(0)

  useEffect(
    () => () => {
      activeAbort.current?.abort()
    },
    [],
  )

  const analyze = (file: File) => {
    activeAbort.current?.abort()
    const abortController = new AbortController()
    const currentRun = runId.current + 1
    runId.current = currentRun
    activeAbort.current = abortController
    progressRef.current = initialProgress
    setScreen({ view: 'scanning', file, progress: initialProgress })

    void controllerFactory()
      .analyze(
        file,
        {
          onProgress: (progress) => {
            if (runId.current !== currentRun) return
            progressRef.current = progress
            setScreen({ view: 'scanning', file, progress })
          },
        },
        abortController.signal,
      )
      .then((result) => {
        if (runId.current !== currentRun) return
        activeAbort.current = null
        setScreen({ view: 'result', file, result })
      })
      .catch((error: unknown) => {
        if (runId.current !== currentRun) return
        activeAbort.current = null
        if (error instanceof AnalysisCancelledError) {
          setScreen({
            view: 'result',
            file,
            result: cancelledResult(progressRef.current),
          })
          return
        }

        setScreen({
          view: 'error',
          file,
          message:
            error instanceof Error
              ? error.message
              : 'The video could not be analyzed.',
        })
      })
  }

  const chooseAnother = () => {
    activeAbort.current?.abort()
    activeAbort.current = null
    runId.current += 1
    setScreen({ view: 'source', file: null })
  }

  return (
    <main className="app-shell" id="main-content">
      <div className="workflow">
        {screen.view === 'source' ? (
          <SourceScreen
            selectedFile={screen.file}
            onAnalyze={analyze}
            onFileChange={(file) => {
              setScreen({ view: 'source', file })
            }}
          />
        ) : null}

        {screen.view === 'scanning' ? (
          <ScanningScreen
            file={screen.file}
            progress={screen.progress}
            onCancel={() => {
              activeAbort.current?.abort()
            }}
          />
        ) : null}

        {screen.view === 'result' ? (
          <ResultScreen
            file={screen.file}
            result={screen.result}
            onAnalyzeAgain={() => {
              analyze(screen.file)
            }}
            onChooseAnother={chooseAnother}
          />
        ) : null}

        {screen.view === 'error' ? (
          <ErrorScreen
            message={screen.message}
            onRetry={() => {
              analyze(screen.file)
            }}
            onChooseAnother={chooseAnother}
          />
        ) : null}
      </div>
    </main>
  )
}

function PageHeader({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string
  title: string
  description: string
}) {
  return (
    <header className="hero">
      <div className="hero-copy">
        <p className="privacy-label">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="lede">{description}</p>
      </div>
    </header>
  )
}

function SourceScreen({
  selectedFile,
  onFileChange,
  onAnalyze,
}: {
  selectedFile: File | null
  onFileChange: (file: File | null) => void
  onAnalyze: (file: File) => void
}) {
  const [sourceMode, setSourceMode] = useState<SourceMode>('file')
  const fileInputId = useId()
  const urlInputId = useId()

  return (
    <>
      <PageHeader
        eyebrow="Runs privately on this device"
        title="Video safety check"
        description="Analyze a video for inappropriate visual content directly on this device."
      />

      <section className="workflow-card" aria-labelledby="source-title">
        <div className="card-header">
          <div>
            <p className="eyebrow">Source</p>
            <h2 id="source-title">Choose a video</h2>
          </div>
          <span className="status-badge">Local processing</span>
        </div>

        <SourceSelector selectedMode={sourceMode} onSelect={setSourceMode} />

        {sourceMode === 'file' ? (
          selectedFile === null ? (
            <FilePicker inputId={fileInputId} onSelect={onFileChange} />
          ) : (
            <SelectedVideoCard
              file={selectedFile}
              inputId={fileInputId}
              onChange={onFileChange}
              onRemove={() => {
                onFileChange(null)
              }}
              onAnalyze={() => {
                onAnalyze(selectedFile)
              }}
            />
          )
        ) : (
          <UrlModePanel inputId={urlInputId} />
        )}
      </section>

      <section className="status-card" aria-labelledby="status-title">
        <div className="card-header">
          <div>
            <p className="eyebrow">Readiness</p>
            <h2 id="status-title">Safety-check status</h2>
          </div>
          <span className="status-badge subdued">
            {selectedFile === null ? 'Waiting' : 'Ready'}
          </span>
        </div>

        <ol className="readiness-list" aria-label="Safety-check readiness">
          <ReadinessItem
            label="Source"
            detail={
              selectedFile === null ? 'Waiting for video' : 'Video selected'
            }
            state={selectedFile === null ? 'active' : 'ready'}
          />
          <ReadinessItem
            label="Model"
            detail="Checked when analysis starts"
            state={selectedFile === null ? 'waiting' : 'active'}
          />
          <ReadinessItem
            label="Analysis"
            detail={selectedFile === null ? 'Waiting' : 'Ready to start'}
            state={selectedFile === null ? 'waiting' : 'ready'}
          />
          <ReadinessItem
            label="Result"
            detail="No decision yet"
            state="waiting"
          />
        </ol>

        <p className="live-status" aria-live="polite">
          {selectedFile === null
            ? 'Choose a video to prepare the local safety check.'
            : 'Video selected. Preview stays hidden while the local scan runs.'}
        </p>
      </section>
    </>
  )
}

function ReadinessItem({
  label,
  detail,
  state,
}: {
  label: string
  detail: string
  state: 'ready' | 'active' | 'waiting'
}) {
  return (
    <li className={`readiness-item is-${state}`}>
      <span className="readiness-dot" aria-hidden="true" />
      <span>
        <strong>{label}</strong>
        <small>{detail}</small>
      </span>
    </li>
  )
}

function SourceSelector({
  selectedMode,
  onSelect,
}: {
  selectedMode: SourceMode
  onSelect: (mode: SourceMode) => void
}) {
  return (
    <div
      className="source-selector"
      role="group"
      aria-label="Video source type"
    >
      <button
        aria-pressed={selectedMode === 'file'}
        className={selectedMode === 'file' ? 'is-selected' : ''}
        type="button"
        onClick={() => {
          onSelect('file')
        }}
      >
        File
      </button>
      <button
        aria-describedby="url-mode-note"
        aria-pressed={selectedMode === 'url'}
        className={selectedMode === 'url' ? 'is-selected' : ''}
        type="button"
        onClick={() => {
          onSelect('url')
        }}
      >
        Video URL
      </button>
    </div>
  )
}

function FilePicker({
  inputId,
  onSelect,
}: {
  inputId: string
  onSelect: (file: File) => void
}) {
  return (
    <label className="file-picker" htmlFor={inputId}>
      <span className="file-icon" aria-hidden="true" />
      <span className="file-picker-copy">
        <strong>Choose a video</strong>
        <span>MP4, WebM, MOV, or any format supported by your browser.</span>
      </span>
      <span className="button-like">Select video</span>
      <input
        accept="video/*"
        aria-label="Select video file"
        id={inputId}
        name="video-source"
        type="file"
        onChange={(event) => {
          const file = event.currentTarget.files?.[0]
          if (file !== undefined) onSelect(file)
        }}
      />
    </label>
  )
}

function SelectedVideoCard({
  file,
  inputId,
  onChange,
  onRemove,
  onAnalyze,
}: {
  file: File
  inputId: string
  onChange: (file: File) => void
  onRemove: () => void
  onAnalyze: () => void
}) {
  return (
    <div className="selected-card">
      <ProtectedPreview fileName={file.name} />

      <div className="selected-meta">
        <div>
          <p className="selected-title">{file.name}</p>
          <p className="selected-summary">
            {file.type || 'Unknown video type'} · {formatFileSize(file.size)}
          </p>
        </div>

        <dl className="metadata-grid" aria-label="Selected file details">
          <MetadataItem label="Type" value={file.type || 'Unknown'} />
          <MetadataItem label="Size" value={formatFileSize(file.size)} />
          <MetadataItem
            label="Modified"
            value={dateFormatter.format(file.lastModified)}
          />
        </dl>
      </div>

      <div className="action-row">
        <label className="secondary-button" htmlFor={inputId}>
          Change
          <input
            accept="video/*"
            aria-label="Change selected video file"
            id={inputId}
            name="video-source"
            type="file"
            onChange={(event) => {
              const nextFile = event.currentTarget.files?.[0]
              if (nextFile !== undefined) onChange(nextFile)
            }}
          />
        </label>
        <button className="secondary-button" type="button" onClick={onRemove}>
          Remove
        </button>
      </div>

      <button className="primary-action" type="button" onClick={onAnalyze}>
        Analyze video
      </button>
    </div>
  )
}

function ProtectedPreview({ fileName }: { fileName: string }) {
  return (
    <div className="protected-preview" aria-label="Protected video preview">
      <span className="hidden-icon" aria-hidden="true" />
      <span className="preview-label">Preview hidden</span>
      <span className="preview-caption">
        {fileName} stays covered until an approved safety check clears playback.
      </span>
    </div>
  )
}

function UrlModePanel({ inputId }: { inputId: string }) {
  return (
    <div className="url-panel">
      <label htmlFor={inputId}>
        <span>Direct video URL</span>
        <input
          aria-describedby="url-mode-note"
          autoComplete="off"
          disabled
          id={inputId}
          name="remote-source"
          placeholder="URL mode is reserved for a later milestone"
          type="url"
        />
      </label>
      <p id="url-mode-note">
        Direct CORS-enabled video URLs remain reserved for a later milestone.
      </p>
    </div>
  )
}

function ScanningScreen({
  file,
  progress,
  onCancel,
}: {
  file: File
  progress: AnalysisProgress
  onCancel: () => void
}) {
  const phaseLabel = {
    preparing: 'Preparing local video',
    'loading-model': 'Loading model runtime',
    scanning: 'Checking video coverage',
    refining: 'Confirming a region',
  }[progress.phase]

  return (
    <>
      <PageHeader
        eyebrow="Nothing leaves this device"
        title="Analyzing video"
        description="Keep this page open while frames are sampled and checked locally."
      />
      <section
        className="workflow-card scanning-card"
        aria-labelledby="scan-title"
      >
        <div className="card-header">
          <div>
            <p className="eyebrow">In progress</p>
            <h2 id="scan-title">{phaseLabel}</h2>
          </div>
          <span className="status-badge">{progress.percent}%</span>
        </div>

        <ProtectedPreview fileName={file.name} />

        <div className="progress-block">
          <progress
            aria-label="Video analysis progress"
            max={100}
            value={progress.percent}
          />
          <div className="progress-copy">
            <span>{phaseLabel}</span>
            <span>
              {progress.completedSamples} / {progress.plannedSamples || '—'}{' '}
              samples
            </span>
          </div>
        </div>

        <p className="live-status" aria-live="polite">
          {phaseLabel}. {progress.completedSamples} samples completed.
        </p>

        <button
          className="secondary-button full-width"
          type="button"
          onClick={onCancel}
        >
          Cancel analysis
        </button>
      </section>
    </>
  )
}

function ResultScreen({
  file,
  result,
  onAnalyzeAgain,
  onChooseAnother,
}: {
  file: File
  result: AnalysisResult
  onAnalyzeAgain: () => void
  onChooseAnother: () => void
}) {
  const [revealRequested, setRevealRequested] = useState(false)
  const [revealed, setRevealed] = useState(false)
  const revealButton = useRef<HTMLButtonElement>(null)
  const cancelled = result.reason === 'cancelled'
  const playbackAllowed =
    (result.modelMode === 'approved' && result.decision === 'safe') || revealed

  const content = resultContent(result)

  return (
    <>
      <PageHeader
        eyebrow={
          cancelled
            ? 'Analysis stopped'
            : result.modelMode === 'demo'
              ? 'Demo mode'
              : 'Local analysis complete'
        }
        title={content.title}
        description={content.description}
      />

      <section className={`workflow-card result-card result-${content.tone}`}>
        <div className="result-heading">
          <span className="result-icon" aria-hidden="true" />
          <div>
            <p className="eyebrow">Result</p>
            <h2>{content.heading}</h2>
          </div>
        </div>

        {playbackAllowed ? (
          <VideoPlayback
            file={file}
            forceMuted={result.decision === 'sensitive'}
          />
        ) : (
          <ProtectedPreview fileName={file.name} />
        )}

        <p className="result-message" aria-live="polite">
          {content.message}
        </p>

        {result.confidence !== undefined ? (
          <p className="confidence-note">
            Heuristic confidence: {percentFormatter.format(result.confidence)}.
            This value is not calibrated on held-out video.
          </p>
        ) : null}

        <details className="technical-details">
          <summary>Technical details</summary>
          <dl>
            <MetadataItem label="Model" value={result.modelLabel} />
            <MetadataItem
              label="Samples"
              value={`${String(result.completedSamples)} / ${String(result.plannedSamples)}`}
            />
            <MetadataItem
              label="Coverage"
              value={
                result.completedSamples === result.plannedSamples &&
                result.plannedSamples > 0
                  ? 'Complete'
                  : 'Incomplete'
              }
            />
          </dl>
        </details>

        {result.modelMode === 'approved' &&
        result.decision === 'sensitive' &&
        !revealed ? (
          <button
            ref={revealButton}
            className="danger-button"
            type="button"
            onClick={() => {
              setRevealRequested(true)
            }}
          >
            Reveal video
          </button>
        ) : null}

        <div className="action-row">
          <button
            className="secondary-button"
            type="button"
            onClick={onChooseAnother}
          >
            Choose another
          </button>
          <button
            className="primary-action"
            type="button"
            onClick={onAnalyzeAgain}
          >
            {cancelled ? 'Restart analysis' : 'Analyze again'}
          </button>
        </div>
      </section>

      <RevealDialog
        open={revealRequested}
        trigger={revealButton}
        onCancel={() => {
          setRevealRequested(false)
        }}
        onConfirm={() => {
          setRevealRequested(false)
          setRevealed(true)
        }}
      />
    </>
  )
}

function resultContent(result: AnalysisResult): {
  title: string
  heading: string
  description: string
  message: string
  tone: 'neutral' | 'safe' | 'warning'
} {
  if (result.modelMode === 'demo') {
    if (result.reason === 'cancelled') {
      return {
        title: 'Analysis cancelled',
        heading: 'No decision was made',
        description: 'The local scan stopped and its resources were released.',
        message:
          'Playback remains covered. You can restart whenever you are ready.',
        tone: 'neutral',
      }
    }
    return {
      title: 'Demo scan complete',
      heading: 'A model is still required',
      description:
        'The browser pipeline completed without an approved model artifact.',
      message:
        'This was a pipeline demonstration, not a content-safety decision. Playback remains covered.',
      tone: 'neutral',
    }
  }

  if (result.decision === 'safe') {
    return {
      title: 'No sensitive content detected',
      heading: 'Playback is available',
      description: 'The approved local model completed whole-video sampling.',
      message:
        'No sampled frame crossed the current threshold. This does not guarantee that the entire video is safe.',
      tone: 'safe',
    }
  }

  if (result.decision === 'sensitive') {
    return {
      title: 'Sensitive content detected',
      heading: 'Playback remains hidden',
      description:
        'Confirming evidence crossed the current local policy threshold.',
      message:
        'The video is paused, muted, and covered. Reveal it only if you understand the warning.',
      tone: 'warning',
    }
  }

  return {
    title: 'Analysis inconclusive',
    heading: 'Playback remains hidden',
    description: 'The scan could not produce a confirmed safety decision.',
    message:
      result.reason === 'timeout'
        ? 'The bounded scan timed out before complete coverage.'
        : 'One elevated sample could not be confirmed by neighboring samples.',
    tone: 'warning',
  }
}

function RevealDialog({
  open,
  trigger,
  onCancel,
  onConfirm,
}: {
  open: boolean
  trigger: RefObject<HTMLButtonElement | null>
  onCancel: () => void
  onConfirm: () => void
}) {
  const dialog = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const element = dialog.current
    if (element === null) return
    if (open && !element.open) element.showModal()
    if (!open && element.open) element.close()
  }, [open])

  return (
    <dialog
      ref={dialog}
      aria-labelledby="reveal-title"
      className="reveal-dialog"
      onCancel={(event) => {
        event.preventDefault()
        onCancel()
        trigger.current?.focus()
      }}
      onClose={() => {
        if (open) onCancel()
        trigger.current?.focus()
      }}
    >
      <h2 id="reveal-title">Reveal potentially sensitive video?</h2>
      <p>
        The video may contain explicit visual content. It will remain muted.
      </p>
      <div className="dialog-actions">
        <button className="secondary-button" type="button" onClick={onCancel}>
          Keep hidden
        </button>
        <button className="danger-button" type="button" onClick={onConfirm}>
          Reveal muted video
        </button>
      </div>
    </dialog>
  )
}

function VideoPlayback({
  file,
  forceMuted,
}: {
  file: File
  forceMuted: boolean
}) {
  const [url] = useState(() => URL.createObjectURL(file))

  useEffect(
    () => () => {
      URL.revokeObjectURL(url)
    },
    [url],
  )

  return (
    <video
      aria-label="Analyzed local video"
      className="result-video"
      controls
      muted={forceMuted}
      playsInline
      src={url}
    />
  )
}

function ErrorScreen({
  message,
  onRetry,
  onChooseAnother,
}: {
  message: string
  onRetry: () => void
  onChooseAnother: () => void
}) {
  return (
    <>
      <PageHeader
        eyebrow="Local analysis stopped"
        title="Video could not be analyzed"
        description="Playback remains hidden and no safety decision was made."
      />
      <section className="workflow-card error-card" role="alert">
        <h2>Check the video or model setup</h2>
        <p className="result-message">{message}</p>
        <div className="action-row">
          <button
            className="secondary-button"
            type="button"
            onClick={onChooseAnother}
          >
            Choose another
          </button>
          <button className="primary-action" type="button" onClick={onRetry}>
            Try again
          </button>
        </div>
      </section>
    </>
  )
}

function MetadataItem({ label, value }: MetadataItemProps) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </>
  )
}

export default App
