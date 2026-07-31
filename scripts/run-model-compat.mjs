import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  parseArguments,
  runCompatibilityCommand,
} from './model-compat-runner.mjs'

async function main() {
  const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
  const argumentsMap = parseArguments(process.argv.slice(2))
  const report = await runCompatibilityCommand({
    policyPath: resolve(argumentsMap.get('policy')),
    artifactPath: resolve(argumentsMap.get('artifact')),
    outputPath: resolve(argumentsMap.get('output')),
    repositoryRoot,
    moduleUrl: import.meta.url,
  })
  process.stdout.write(
    `${JSON.stringify(
      {
        releaseId: report.releaseId,
        artifact: report.artifact,
        runtime: report.runtime,
        browser: report.browser,
        tensorContract: report.tensorContract,
        benchmark: report.benchmark,
        compatibility: report.compatibility,
      },
      null,
      2,
    )}\n`,
  )
}

main().catch(() => {
  process.stderr.write('Protected model compatibility failed.\n')
  process.exitCode = 1
})
