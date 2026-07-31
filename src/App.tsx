import { useId, useState } from 'react'

type SourceMode = 'file' | 'url'
type UiState = 'idle' | 'source-selected' | 'blocked-pending-model'
type ReadinessState = 'ready' | 'active' | 'waiting'

interface ReadinessItem {
  label: string
  detail: string
  state: ReadinessState
}

interface MetadataItemProps {
  label: string
  value: string
}

const bytesFormatter = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 1,
})

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
})

function formatFileSize(bytes: number) {
  if (bytes === 0) {
    return '0 B'
  }

  const units = ['B', 'KB', 'MB', 'GB'] as const
  const exponent = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  )
  const value = bytes / 1024 ** exponent
  const unit = units[exponent] ?? 'GB'

  return `${bytesFormatter.format(value)} ${unit}`
}

function getUiState(selectedFile: File | null): UiState {
  return selectedFile === null ? 'idle' : 'source-selected'
}

function getStatusMessage(selectedFile: File | null) {
  if (selectedFile === null) {
    return 'Choose a video to prepare the local safety check.'
  }

  return `${selectedFile.name} is selected. Preview stays hidden until a future safety check clears playback.`
}

function getReadiness(selectedFile: File | null): ReadinessItem[] {
  return [
    {
      label: 'Source',
      detail: selectedFile === null ? 'Waiting for video' : 'Video selected',
      state: selectedFile === null ? 'active' : 'ready',
    },
    {
      label: 'Model',
      detail: 'Artifact pending',
      state: selectedFile === null ? 'waiting' : 'active',
    },
    {
      label: 'Analysis',
      detail: 'Disabled until baseline release',
      state: 'waiting',
    },
    {
      label: 'Result',
      detail: 'No decision yet',
      state: 'waiting',
    },
  ]
}

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [sourceMode, setSourceMode] = useState<SourceMode>('file')
  const fileInputId = useId()
  const urlInputId = useId()
  const uiState = getUiState(selectedFile)
  const readiness = getReadiness(selectedFile)
  const statusMessage = getStatusMessage(selectedFile)
  const analysisBlocked = uiState === 'source-selected'

  return (
    <main className="app-shell" id="main-content">
      <section className="workflow" aria-labelledby="page-title">
        <header className="hero">
          <div className="hero-copy">
            <p className="privacy-label">Runs privately on this device</p>
            <h1 id="page-title">Video safety check</h1>
            <p className="lede">
              Analyze a video for inappropriate visual content directly on this
              device.
            </p>
          </div>
        </header>

        <section className="workflow-card" aria-labelledby="source-title">
          <div className="card-header">
            <div>
              <p className="eyebrow">Source</p>
              <h2 id="source-title">Choose a video</h2>
            </div>
            <span className="status-badge">Local processing</span>
          </div>

          <SourceSelector
            selectedMode={sourceMode}
            onSelect={(mode) => {
              setSourceMode(mode)
            }}
          />

          {sourceMode === 'file' ? (
            selectedFile === null ? (
              <FilePicker
                inputId={fileInputId}
                onSelect={(file) => {
                  setSelectedFile(file)
                }}
              />
            ) : (
              <SelectedVideoCard
                file={selectedFile}
                inputId={fileInputId}
                analysisBlocked={analysisBlocked}
                onChange={(file) => {
                  setSelectedFile(file)
                }}
                onRemove={() => {
                  setSelectedFile(null)
                }}
              />
            )
          ) : (
            <UrlModePanel inputId={urlInputId} />
          )}

          {analysisBlocked ? (
            <p className="blocked-note" id="analysis-blocked-note">
              Model artifact pending. Analysis will be enabled after the
              baseline release milestone is complete.
            </p>
          ) : null}
        </section>

        <section className="status-card" aria-labelledby="status-title">
          <div className="card-header">
            <div>
              <p className="eyebrow">Readiness</p>
              <h2 id="status-title">Safety-check status</h2>
            </div>
            <span className="status-badge subdued">
              {uiState === 'idle' ? 'Waiting' : 'Prepared'}
            </span>
          </div>

          <ol className="readiness-list" aria-label="Safety-check readiness">
            {readiness.map((item) => (
              <li
                className={`readiness-item is-${item.state}`}
                key={item.label}
              >
                <span className="readiness-dot" aria-hidden="true" />
                <span>
                  <strong>{item.label}</strong>
                  <small>{item.detail}</small>
                </span>
              </li>
            ))}
          </ol>

          <p className="live-status" aria-live="polite">
            {statusMessage}
          </p>

          <details className="technical-details">
            <summary>Technical details</summary>
            <dl>
              <MetadataItem label="Model" value="No artifact" />
              <MetadataItem label="Scan" value="Disabled" />
              <MetadataItem label="Samples" value="0 / 0" />
              <MetadataItem label="Coverage" value="0%" />
              <MetadataItem
                label="Selected file"
                value={
                  selectedFile === null
                    ? 'None'
                    : formatFileSize(selectedFile.size)
                }
              />
            </dl>
          </details>
        </section>
      </section>
    </main>
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

          if (file !== undefined) {
            onSelect(file)
          }
        }}
      />
    </label>
  )
}

function SelectedVideoCard({
  file,
  inputId,
  analysisBlocked,
  onChange,
  onRemove,
}: {
  file: File
  inputId: string
  analysisBlocked: boolean
  onChange: (file: File) => void
  onRemove: () => void
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

              if (nextFile !== undefined) {
                onChange(nextFile)
              }
            }}
          />
        </label>
        <button className="secondary-button" type="button" onClick={onRemove}>
          Remove
        </button>
      </div>

      <button
        aria-describedby={analysisBlocked ? 'analysis-blocked-note' : undefined}
        className="primary-action"
        disabled={analysisBlocked}
        type="button"
      >
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
        {fileName} stays covered until analysis can verify playback.
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
        Enter a direct video URL. The host must allow browser access. URL
        analysis is not enabled in this scaffold.
      </p>
    </div>
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
