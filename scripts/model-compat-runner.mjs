import { createHash } from 'node:crypto'
import {
  constants,
  copyFile,
  cp,
  mkdtemp,
  open,
  readFile,
  rm,
  stat,
} from 'node:fs/promises'
import { createRequire } from 'node:module'
import { tmpdir } from 'node:os'
import { dirname, isAbsolute, join, relative, resolve, sep } from 'node:path'

import { chromium } from '@playwright/test'
import { createServer } from 'vite'

export function parseArguments(argv) {
  const values = new Map()
  for (let index = 0; index < argv.length; index += 2) {
    const name = argv[index]
    const value = argv[index + 1]
    if (!name?.startsWith('--') || !value || values.has(name.slice(2))) {
      throw new Error('Invalid compatibility arguments')
    }
    values.set(name.slice(2), value)
  }
  for (const required of ['policy', 'artifact', 'output']) {
    if (!values.has(required)) {
      throw new Error('Missing required compatibility argument')
    }
  }
  return values
}

function isWithin(candidate, parent) {
  const path = relative(resolve(parent), resolve(candidate))
  return (
    path === '' ||
    (!path.startsWith(`..${sep}`) && path !== '..' && !isAbsolute(path))
  )
}

export async function validateProtectedPaths(
  artifactPath,
  outputPath,
  repositoryRoot,
  temporaryRoot = tmpdir(),
) {
  for (const path of [artifactPath, outputPath]) {
    if (isWithin(path, repositoryRoot)) {
      throw new Error('Protected path is inside the Git worktree')
    }
    if (isWithin(path, temporaryRoot)) {
      throw new Error('Protected path is in temporary storage')
    }
  }
  const artifactInfo = await stat(artifactPath)
  if (!artifactInfo.isFile())
    throw new Error('Protected artifact is not a file')
  const outputParent = await stat(dirname(outputPath))
  if (!outputParent.isDirectory()) {
    throw new Error('Compatibility output parent is not a directory')
  }
  try {
    await stat(outputPath)
    throw new Error('Compatibility output already exists')
  } catch (error) {
    if (error.code !== 'ENOENT') throw error
  }
}

export function validatePolicy(policy) {
  const requiredStrings = [
    policy.releaseId,
    policy.modelId,
    policy.semanticVersion,
    policy.runtime?.package,
    policy.runtime?.version,
  ]
  if (
    policy.schemaVersion !== 1 ||
    requiredStrings.some((value) => typeof value !== 'string' || !value) ||
    policy.runtime.accelerator !== 'wasm' ||
    policy.runtime.browser !== 'chromium' ||
    policy.input?.dtype !== 'float32' ||
    policy.output?.dtype !== 'float32' ||
    policy.output?.semantics !== 'probabilities' ||
    !validShape(policy.input?.shape) ||
    !validShape(policy.output?.shape) ||
    !positiveInteger(policy.runtime.warmupIterations) ||
    !positiveInteger(policy.runtime.measuredIterations)
  ) {
    throw new Error('Compatibility policy is invalid')
  }
  return policy
}

function validShape(value) {
  return (
    Array.isArray(value) &&
    value.length > 0 &&
    value.every((dimension) => positiveInteger(dimension))
  )
}

function positiveInteger(value) {
  return Number.isInteger(value) && value > 0
}

export async function loadRuntime(policy, moduleUrl) {
  const require = createRequire(moduleUrl)
  const packagePath = require.resolve(`${policy.runtime.package}/package.json`)
  const packageMetadata = JSON.parse(await readFile(packagePath, 'utf8'))
  if (packageMetadata.version !== policy.runtime.version) {
    throw new Error('Installed LiteRT.js version does not match policy')
  }
  return dirname(packagePath)
}

function compatibilityContract(policy) {
  return {
    inputShape: policy.input.shape,
    outputShape: policy.output.shape,
    inputDType: policy.input.dtype,
    outputDType: policy.output.dtype,
    warmupIterations: policy.runtime.warmupIterations,
    measuredIterations: policy.runtime.measuredIterations,
  }
}

function contentType(path) {
  if (path.endsWith('.wasm')) return 'application/wasm'
  if (path.endsWith('.js')) return 'text/javascript; charset=utf-8'
  if (path.endsWith('.json')) return 'application/json; charset=utf-8'
  return 'application/octet-stream'
}

export function protectedAssetPlugin(stagingDirectory) {
  return {
    name: 'bbcds-protected-model-assets',
    configureServer(server) {
      server.middlewares.use(async (request, response, next) => {
        const url = request.url?.split('?')[0]
        const assetPath = resolveProtectedAsset(url, stagingDirectory)
        if (!assetPath) return next()
        try {
          const contents = await readFile(assetPath)
          response.statusCode = 200
          response.setHeader('Content-Type', contentType(assetPath))
          response.setHeader('Cache-Control', 'no-store')
          response.end(contents)
        } catch {
          response.statusCode = 404
          response.end()
        }
      })
    },
  }
}

export function resolveProtectedAsset(url, stagingDirectory) {
  if (url === '/protected-model.tflite') {
    return join(stagingDirectory, 'protected-model.tflite')
  }
  if (url === '/compat-policy.json') {
    return join(stagingDirectory, 'compat-policy.json')
  }
  if (!url?.startsWith('/litert-wasm/')) return undefined
  const name = url.slice('/litert-wasm/'.length)
  if (!name || name.includes('/') || name.includes('..')) return undefined
  return join(stagingDirectory, 'litert-wasm', name)
}

export async function writeExclusiveJson(path, value) {
  let handle
  let created = false
  try {
    handle = await open(
      path,
      constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL,
      0o600,
    )
    created = true
    await handle.writeFile(`${JSON.stringify(value, null, 2)}\n`, 'utf8')
  } catch (error) {
    if (created) await rm(path, { force: true })
    throw error
  } finally {
    await handle?.close()
  }
}

export async function withStagingDirectory(action, temporaryRoot = tmpdir()) {
  const directory = await mkdtemp(join(temporaryRoot, 'bbcds-model-compat-'))
  try {
    return await action(directory)
  } finally {
    await rm(directory, { recursive: true, force: true })
  }
}

async function sha256(path) {
  const digest = createHash('sha256')
  digest.update(await readFile(path))
  return digest.digest('hex')
}

export async function runCompatibilityCommand({
  policyPath,
  artifactPath,
  outputPath,
  repositoryRoot,
  moduleUrl,
}) {
  await validateProtectedPaths(artifactPath, outputPath, repositoryRoot)
  const policy = validatePolicy(JSON.parse(await readFile(policyPath, 'utf8')))
  const runtimeRoot = await loadRuntime(policy, moduleUrl)
  return withStagingDirectory(async (stagingDirectory) => {
    let viteServer
    let browser
    try {
      await copyFile(
        artifactPath,
        join(stagingDirectory, 'protected-model.tflite'),
        constants.COPYFILE_EXCL,
      )
      await cp(
        join(runtimeRoot, 'wasm'),
        join(stagingDirectory, 'litert-wasm'),
        {
          recursive: true,
          errorOnExist: true,
        },
      )
      await writeExclusiveJson(
        join(stagingDirectory, 'compat-policy.json'),
        compatibilityContract(policy),
      )
      viteServer = await createServer({
        root: repositoryRoot,
        logLevel: 'silent',
        server: { host: '127.0.0.1', port: 0, strictPort: false },
        plugins: [protectedAssetPlugin(stagingDirectory)],
      })
      await viteServer.listen()
      const address = viteServer.httpServer.address()
      if (!address || typeof address === 'string') {
        throw new Error('Compatibility server did not start')
      }
      browser = await chromium.launch()
      const page = await browser.newPage()
      await page.goto(
        `http://127.0.0.1:${address.port}/tests/model-compat/index.html`,
      )
      const result = await page.evaluate(
        () => globalThis.__BBCDS_MODEL_COMPATIBILITY__,
      )
      const artifactInfo = await stat(artifactPath)
      const report = {
        schemaVersion: 1,
        releaseId: policy.releaseId,
        modelId: policy.modelId,
        semanticVersion: policy.semanticVersion,
        artifact: {
          sha256: await sha256(artifactPath),
          sizeBytes: artifactInfo.size,
        },
        runtime: {
          package: policy.runtime.package,
          version: policy.runtime.version,
          accelerator: policy.runtime.accelerator,
        },
        browser: {
          name: policy.runtime.browser,
          version: browser.version(),
          platform: `${process.platform}-${process.arch}`,
        },
        ...result,
      }
      if (!report.compatibility.passed) {
        throw new Error('Compatibility gates did not pass')
      }
      await writeExclusiveJson(outputPath, report)
      return report
    } finally {
      await browser?.close()
      await viteServer?.close()
    }
  })
}
