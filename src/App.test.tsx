import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import App from './App'

describe('App', () => {
  it('renders the protected video safety-check scaffold', () => {
    render(<App />)

    expect(
      screen.getByRole('heading', { name: 'Video safety check' }),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Runs privately on this device'),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'File' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByRole('button', { name: 'Video URL' })).toHaveAttribute(
      'aria-pressed',
      'false',
    )
    expect(screen.getByText('No artifact')).toBeInTheDocument()
    expect(document.querySelector('video')).not.toBeInTheDocument()
  })

  it('shows selected file metadata without exposing a video preview', async () => {
    const user = userEvent.setup()
    const file = new File(['video'], 'sample-intake.mp4', {
      lastModified: new Date('2026-07-30T10:00:00Z').getTime(),
      type: 'video/mp4',
    })

    render(<App />)

    await user.upload(screen.getByLabelText('Select video file'), file)

    expect(screen.getByText('sample-intake.mp4')).toBeInTheDocument()
    const fileDetails = screen.getByLabelText('Selected file details')
    expect(within(fileDetails).getByText('video/mp4')).toBeInTheDocument()
    expect(within(fileDetails).getByText('5 B')).toBeInTheDocument()
    expect(screen.getByText('Preview hidden')).toBeInTheDocument()
    expect(screen.getByLabelText('Protected video preview')).toBeInTheDocument()
    expect(document.querySelector('video')).not.toBeInTheDocument()
  })

  it('keeps analysis disabled until the model artifact milestone', async () => {
    const user = userEvent.setup()
    const file = new File(['video'], 'sample-intake.mp4', {
      type: 'video/mp4',
    })

    render(<App />)

    await user.upload(screen.getByLabelText('Select video file'), file)

    expect(screen.getByRole('button', { name: 'Analyze video' })).toBeDisabled()
    expect(screen.getByText(/Model artifact pending/i)).toBeInTheDocument()
    expect(screen.getByText(/model artifact milestone/i)).toBeInTheDocument()
  })

  it('clears the selected file when remove is activated', async () => {
    const user = userEvent.setup()
    const file = new File(['video'], 'sample-intake.mp4', {
      type: 'video/mp4',
    })

    render(<App />)

    await user.upload(screen.getByLabelText('Select video file'), file)
    await user.click(screen.getByRole('button', { name: 'Remove' }))

    expect(screen.getByLabelText('Select video file')).toBeInTheDocument()
    expect(screen.queryByText('sample-intake.mp4')).not.toBeInTheDocument()
    expect(screen.queryByText('Preview hidden')).not.toBeInTheDocument()
  })

  it('explains that URL analysis is reserved for a later milestone', async () => {
    const user = userEvent.setup()

    render(<App />)

    await user.click(screen.getByRole('button', { name: 'Video URL' }))

    expect(screen.getByRole('button', { name: 'Video URL' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByLabelText('Direct video URL')).toBeDisabled()
    expect(screen.getByText(/URL analysis is not enabled/i)).toBeInTheDocument()
  })

  it('keeps technical details collapsed by default', () => {
    render(<App />)

    const details = screen.getByText('Technical details').closest('details')

    expect(details).not.toHaveAttribute('open')
    expect(
      within(screen.getByLabelText('Safety-check readiness')).getByText(
        'Model',
      ),
    ).toBeInTheDocument()
  })
})
