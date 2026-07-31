import { rm } from 'node:fs/promises'
import { resolve } from 'node:path'

const repositoryRoot = resolve(import.meta.dirname, '..')
const generatedPaths = [
  'coverage',
  'dist',
  'dist-ssr',
  'playwright-report',
  'test-results',
  'model/.mypy_cache',
  'model/.pytest_cache',
  'model/.ruff_cache',
]

async function removePythonCaches(directory) {
  const { readdir } = await import('node:fs/promises')
  const entries = await readdir(directory, { withFileTypes: true })
  await Promise.all(
    entries
      .filter((entry) => entry.isDirectory())
      .map(async (entry) => {
        const path = resolve(directory, entry.name)
        if (entry.name === '__pycache__') {
          await rm(path, { recursive: true, force: true })
        } else if (entry.name !== '.venv') {
          await removePythonCaches(path)
        }
      }),
  )
}

await Promise.all([
  ...generatedPaths.map((path) =>
    rm(resolve(repositoryRoot, path), { recursive: true, force: true }),
  ),
  removePythonCaches(resolve(repositoryRoot, 'model/src')),
  removePythonCaches(resolve(repositoryRoot, 'model/tests')),
])
