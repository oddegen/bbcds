/// <reference lib="dom" />

import { AxeBuilder } from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

async function selectGeneratedBenignVideo(page: Page): Promise<void> {
  await page.evaluate(async () => {
    const input = document.querySelector<HTMLInputElement>(
      'input[aria-label="Select video file"]',
    )
    if (input === null) throw new Error('Video input is missing')

    const canvas = document.createElement('canvas')
    canvas.width = 64
    canvas.height = 64
    const context = canvas.getContext('2d')
    if (context === null) throw new Error('Canvas is unavailable')
    const stream = canvas.captureStream(8)
    const chunks: Blob[] = []
    const recorder = new MediaRecorder(stream, { mimeType: 'video/webm' })
    recorder.addEventListener('dataavailable', (event: BlobEvent) => {
      if (event.data.size > 0) chunks[chunks.length] = event.data
    })
    const stopped = new Promise<void>((resolve) => {
      recorder.addEventListener(
        'stop',
        () => {
          resolve()
        },
        { once: true },
      )
    })

    recorder.start(100)
    for (let frame = 0; frame < 10; frame += 1) {
      context.fillStyle = frame % 2 === 0 ? '#dbeafe' : '#e0f2fe'
      context.fillRect(0, 0, canvas.width, canvas.height)
      await new Promise((resolve) => setTimeout(resolve, 100))
    }
    recorder.stop()
    await stopped
    for (const track of stream.getTracks()) track.stop()

    const selected = new File(chunks, 'generated-benign.webm', {
      type: 'video/webm',
    })
    const transfer = new DataTransfer()
    transfer.items.add(selected)
    input.files = transfer.files
    input.dispatchEvent(new Event('change', { bubbles: true }))
  })
}

test('loads the protected video safety-check shell', async ({ page }) => {
  await page.goto('/')

  await expect(
    page.getByRole('heading', { name: 'Video safety check' }),
  ).toBeVisible()
  await expect(page.getByText('Runs privately on this device')).toBeVisible()
  await expect(
    page.getByRole('button', { exact: true, name: 'File' }),
  ).toHaveAttribute('aria-pressed', 'true')
  await expect(page.locator('video')).toHaveCount(0)
})

test('has no obvious accessibility violations on the app shell', async ({
  page,
}) => {
  await page.goto('/')

  const results = await new AxeBuilder({ page }).analyze()

  expect(results.violations).toEqual([])
})

test('selecting a local video keeps the preview protected', async ({
  page,
}) => {
  await page.goto('/')

  await page.getByLabel('Select video file').setInputFiles({
    buffer: Buffer.from('synthetic benign browser smoke file'),
    mimeType: 'video/mp4',
    name: 'local-intake-smoke.mp4',
  })

  const fileDetails = page.getByLabel('Selected file details')
  await expect(fileDetails.getByText('video/mp4')).toBeVisible()
  await expect(
    page.getByText('local-intake-smoke.mp4', { exact: true }),
  ).toBeVisible()
  await expect(page.getByText('Preview hidden')).toBeVisible()
  await expect(page.getByLabel('Protected video preview')).toBeVisible()
  await expect(page.locator('video')).toHaveCount(0)
  await expect(
    page.getByRole('button', { name: 'Analyze video' }),
  ).toBeEnabled()
})

test('URL mode explains the current milestone boundary', async ({ page }) => {
  await page.goto('/')

  await page.getByRole('button', { name: 'Video URL' }).click()

  await expect(page.getByRole('button', { name: 'Video URL' })).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  await expect(page.getByLabel('Direct video URL')).toBeDisabled()
  await expect(page.getByText(/later milestone/i)).toBeVisible()
})

test('runs a generated local video through the demo worker without a safety claim', async ({
  page,
}) => {
  test.setTimeout(30_000)
  const consoleErrors: string[] = []
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
  })
  page.on('pageerror', (error) => {
    consoleErrors.push(error.message)
  })
  await page.goto('/')
  await selectGeneratedBenignVideo(page)
  await page.getByRole('button', { name: 'Analyze video' }).click()

  await expect(
    page.getByRole('heading', { name: 'Demo scan complete' }),
  ).toBeVisible({
    timeout: 20_000,
  })
  await expect(page.getByText(/not a content-safety decision/i)).toBeVisible()
  await expect(page.getByLabel('Protected video preview')).toBeVisible()
  await expect(page.locator('video')).toHaveCount(0)
  const accessibility = await new AxeBuilder({ page }).analyze()
  expect(accessibility.violations).toEqual([])
  expect(consoleErrors).toEqual([])
})

test('keeps the source flow within a mobile viewport', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 780 })
  await page.goto('/')

  await expect(
    page.getByRole('heading', { name: 'Video safety check' }),
  ).toBeVisible()
  const overflow = await page.evaluate(
    () =>
      document.documentElement.scrollWidth -
      document.documentElement.clientWidth,
  )
  expect(overflow).toBeLessThanOrEqual(0)
})
