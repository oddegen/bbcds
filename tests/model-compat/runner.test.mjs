import { chmod, mkdir, readFile, stat, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'

import { describe, expect, it } from 'vitest'

import {
  loadRuntime,
  parseArguments,
  resolveProtectedAsset,
  validatePolicy,
  validateProtectedPaths,
  withStagingDirectory,
  writeExclusiveJson,
} from '../../scripts/model-compat-runner.mjs'

function policy(version = '2.5.3') {
  return {
    schemaVersion: 1,
    releaseId: 'test-release',
    modelId: 'test-model',
    semanticVersion: '1.0.0',
    input: { shape: [1, 2, 2, 3], dtype: 'float32' },
    output: { shape: [1, 4], dtype: 'float32', semantics: 'probabilities' },
    runtime: {
      package: 'fake-runtime',
      version,
      accelerator: 'wasm',
      browser: 'chromium',
      warmupIterations: 1,
      measuredIterations: 2,
    },
  }
}

describe('compatibility command boundary', () => {
  it('requires one policy, artifact, and output argument', () => {
    expect(
      parseArguments([
        '--policy',
        'policy.json',
        '--artifact',
        'model.tflite',
        '--output',
        'report.json',
      ]).get('policy'),
    ).toBe('policy.json')
    expect(() => parseArguments(['--artifact', 'model.tflite'])).toThrow(
      /Missing required/,
    )
    expect(() =>
      parseArguments(['--policy', 'one', '--policy', 'two']),
    ).toThrow(/Invalid/)
  })

  it('exposes only the staged model, policy, and flat WASM filenames', () => {
    expect(resolveProtectedAsset('/protected-model.tflite', '/stage')).toBe(
      '/stage/protected-model.tflite',
    )
    expect(resolveProtectedAsset('/compat-policy.json', '/stage')).toBe(
      '/stage/compat-policy.json',
    )
    expect(resolveProtectedAsset('/litert-wasm/runtime.wasm', '/stage')).toBe(
      '/stage/litert-wasm/runtime.wasm',
    )
    expect(
      resolveProtectedAsset('/litert-wasm/../secret', '/stage'),
    ).toBeUndefined()
    expect(resolveProtectedAsset('/dataset.csv', '/stage')).toBeUndefined()
  })

  it('rejects invalid policy and installed runtime drift', async () => {
    expect(() =>
      validatePolicy({
        ...policy(),
        runtime: { ...policy().runtime, browser: 'firefox' },
      }),
    ).toThrow(/policy is invalid/)

    await withStagingDirectory(async (directory) => {
      const packageRoot = join(directory, 'node_modules', 'fake-runtime')
      await mkdir(packageRoot, { recursive: true })
      await writeFile(join(directory, 'entry.mjs'), '')
      await writeFile(
        join(packageRoot, 'package.json'),
        JSON.stringify({ name: 'fake-runtime', version: '2.5.2' }),
      )
      await expect(
        loadRuntime(policy(), pathToFileURL(join(directory, 'entry.mjs')).href),
      ).rejects.toThrow(/does not match policy/)
    })
  })

  it('rejects unsafe paths and writes owner-only evidence exclusively', async () => {
    await withStagingDirectory(async (directory) => {
      const repository = join(directory, 'repository')
      const protectedRoot = join(directory, 'protected')
      const temporaryRoot = join(directory, 'temporary')
      await mkdir(repository)
      await mkdir(protectedRoot)
      await mkdir(temporaryRoot)
      const artifact = join(protectedRoot, 'model.tflite')
      const output = join(protectedRoot, 'report.json')
      await writeFile(artifact, 'model')
      await expect(
        validateProtectedPaths(
          artifact,
          join(repository, 'report.json'),
          repository,
          temporaryRoot,
        ),
      ).rejects.toThrow(/worktree/)
      await validateProtectedPaths(artifact, output, repository, temporaryRoot)
      await writeExclusiveJson(output, { passed: true })
      await chmod(output, 0o600)
      expect((await stat(output)).mode & 0o777).toBe(0o600)
      expect(JSON.parse(await readFile(output, 'utf8'))).toEqual({
        passed: true,
      })
      await expect(writeExclusiveJson(output, {})).rejects.toThrow()
    })
  })

  it('cleans staging after failure', async () => {
    let staging
    await expect(
      withStagingDirectory(async (directory) => {
        staging = directory
        throw new Error('synthetic failure')
      }),
    ).rejects.toThrow(/synthetic failure/)
    await expect(stat(staging)).rejects.toMatchObject({ code: 'ENOENT' })
  })
})
