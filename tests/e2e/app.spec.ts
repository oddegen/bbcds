import { AxeBuilder } from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

test('loads the app shell', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Hello' })).toBeVisible()
})

test('has no obvious accessibility violations on the app shell', async ({
  page,
}) => {
  await page.goto('/')

  const results = await new AxeBuilder({ page }).analyze()

  expect(results.violations).toEqual([])
})
