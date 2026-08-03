import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import App from './App'
import {
  AnalysisCancelledError,
  type AnalysisController,
  type AnalysisResult,
} from './analysis/types'

const file = new File(['video'], 'sample-intake.mp4', {
  lastModified: new Date('2026-07-30T10:00:00Z').getTime(),
  type: 'video/mp4',
})

function result(overrides: Partial<AnalysisResult> = {}): AnalysisResult {
  return {
    decision: 'demo',
    modelMode: 'demo',
    modelLabel: 'Demo classifier — no model installed',
    completedSamples: 3,
    plannedSamples: 3,
    durationSeconds: 20,
    ...overrides,
  }
}

function controllerWithResult(value: AnalysisResult): AnalysisController {
  return {
    analyze: (_file, callbacks) => {
      callbacks.onProgress({
        phase: 'scanning',
        completedSamples: 1,
        plannedSamples: 3,
        percent: 33,
      })
      return Promise.resolve(value)
    },
  }
}

beforeEach(() => {
  Object.defineProperty(URL, 'createObjectURL', {
    configurable: true,
    value: vi.fn(() => 'blob:test-video'),
  })
  Object.defineProperty(URL, 'revokeObjectURL', {
    configurable: true,
    value: vi.fn(),
  })
})

describe('App', () => {
  it('selects a local video without exposing a preview and enables analysis', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.upload(screen.getByLabelText('Select video file'), file)

    const fileDetails = screen.getByLabelText('Selected file details')
    expect(within(fileDetails).getByText('video/mp4')).toBeInTheDocument()
    expect(screen.getByText('Preview hidden')).toBeInTheDocument()
    expect(document.querySelector('video')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Analyze video' })).toBeEnabled()
  })

  it('moves through scanning to a covered demo result', async () => {
    const user = userEvent.setup()
    render(<App controllerFactory={() => controllerWithResult(result())} />)

    await user.upload(screen.getByLabelText('Select video file'), file)
    await user.click(screen.getByRole('button', { name: 'Analyze video' }))

    expect(
      await screen.findByRole('heading', { name: 'Demo scan complete' }),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/not a content-safety decision/i),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Protected video preview')).toBeInTheDocument()
    expect(document.querySelector('video')).not.toBeInTheDocument()
  })

  it('cancels a running scan and allows an immediate restart', async () => {
    const user = userEvent.setup()
    const analyze = vi.fn(
      (_file: File, _callbacks: unknown, signal: AbortSignal) =>
        new Promise<AnalysisResult>((_resolve, reject) => {
          signal.addEventListener('abort', () => {
            reject(new AnalysisCancelledError())
          })
        }),
    )
    render(<App controllerFactory={() => ({ analyze })} />)

    await user.upload(screen.getByLabelText('Select video file'), file)
    await user.click(screen.getByRole('button', { name: 'Analyze video' }))
    await user.click(screen.getByRole('button', { name: 'Cancel analysis' }))

    expect(
      await screen.findByRole('heading', { name: 'Analysis cancelled' }),
    ).toBeInTheDocument()
    expect(screen.getByText('No decision was made')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Restart analysis' }),
    ).toBeEnabled()
  })

  it('reveals playback only for an approved safe result', async () => {
    const user = userEvent.setup()
    render(
      <App
        controllerFactory={() =>
          controllerWithResult(
            result({
              decision: 'safe',
              modelMode: 'approved',
              modelLabel: 'approved-model 1.0.0',
              confidence: 0.91,
            }),
          )
        }
      />,
    )

    await user.upload(screen.getByLabelText('Select video file'), file)
    await user.click(screen.getByRole('button', { name: 'Analyze video' }))

    expect(
      await screen.findByRole('heading', {
        name: 'No sensitive content detected',
      }),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Analyzed local video')).toHaveAttribute(
      'src',
      'blob:test-video',
    )
    expect(screen.getByText(/not calibrated/i)).toBeInTheDocument()
  })

  it('fails closed when demo mode receives a contradictory safe decision', async () => {
    const user = userEvent.setup()
    render(
      <App
        controllerFactory={() =>
          controllerWithResult(
            result({ decision: 'safe', modelMode: 'demo', confidence: 1 }),
          )
        }
      />,
    )

    await user.upload(screen.getByLabelText('Select video file'), file)
    await user.click(screen.getByRole('button', { name: 'Analyze video' }))

    expect(
      await screen.findByRole('heading', { name: 'Demo scan complete' }),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Protected video preview')).toBeInTheDocument()
    expect(document.querySelector('video')).not.toBeInTheDocument()
  })

  it('requires confirmation before revealing a sensitive result', async () => {
    const user = userEvent.setup()
    render(
      <App
        controllerFactory={() =>
          controllerWithResult(
            result({
              decision: 'sensitive',
              modelMode: 'approved',
              modelLabel: 'approved-model 1.0.0',
              confidence: 0.78,
              completedSamples: 2,
              plannedSamples: 8,
            }),
          )
        }
      />,
    )

    await user.upload(screen.getByLabelText('Select video file'), file)
    await user.click(screen.getByRole('button', { name: 'Analyze video' }))
    await user.click(
      await screen.findByRole('button', { name: 'Reveal video' }),
    )

    expect(
      screen.getByRole('heading', {
        name: 'Reveal potentially sensitive video?',
      }),
    ).toBeInTheDocument()
    expect(document.querySelector('video')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Reveal muted video' }))
    expect(screen.getByLabelText('Analyzed local video')).toHaveProperty(
      'muted',
      true,
    )
  })

  it('shows a retryable error without revealing playback', async () => {
    const user = userEvent.setup()
    render(
      <App
        controllerFactory={() => ({
          analyze: () =>
            Promise.reject(new Error('Approved model artifact is missing')),
        })}
      />,
    )

    await user.upload(screen.getByLabelText('Select video file'), file)
    await user.click(screen.getByRole('button', { name: 'Analyze video' }))

    expect(
      await screen.findByRole('heading', {
        name: 'Video could not be analyzed',
      }),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Approved model artifact is missing'),
    ).toBeInTheDocument()
    expect(document.querySelector('video')).not.toBeInTheDocument()
  })

  it('keeps direct URL analysis disabled', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: 'Video URL' }))

    expect(screen.getByLabelText('Direct video URL')).toBeDisabled()
    expect(screen.getByText(/later milestone/i)).toBeInTheDocument()
  })
})
