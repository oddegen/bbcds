import { AxeBuilder } from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

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
  ).toBeDisabled()
  await expect(page.getByText(/baseline release milestone/i)).toBeVisible()
})

test('URL mode explains the current milestone boundary', async ({ page }) => {
  await page.goto('/')

  await page.getByRole('button', { name: 'Video URL' }).click()

  await expect(page.getByRole('button', { name: 'Video URL' })).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  await expect(page.getByLabel('Direct video URL')).toBeDisabled()
  await expect(page.getByText(/URL analysis is not enabled/i)).toBeVisible()
})
