import react from '@vitejs/plugin-react'
import { readFileSync } from 'node:fs'
import { basename, join } from 'node:path'
import type { Plugin } from 'vite'
import { defineConfig } from 'vitest/config'

const liteRtAssetNames = [
  'litert_wasm_internal.js',
  'litert_wasm_internal.wasm',
  'litert_wasm_compat_internal.js',
  'litert_wasm_compat_internal.wasm',
] as const

function liteRtAssets(): Plugin {
  const wasmDirectory = join(
    import.meta.dirname,
    'node_modules',
    '@litertjs',
    'core',
    'wasm',
  )
  const allowedAssets = new Set<string>(liteRtAssetNames)

  return {
    name: 'bbcds-litert-assets',
    configureServer(server) {
      server.middlewares.use('/litert-wasm/', (request, response, next) => {
        const assetName = basename(request.url ?? '')
        if (!allowedAssets.has(assetName)) {
          next()
          return
        }

        response.setHeader(
          'Content-Type',
          assetName.endsWith('.wasm')
            ? 'application/wasm'
            : 'text/javascript; charset=utf-8',
        )
        response.end(readFileSync(join(wasmDirectory, assetName)))
      })
    },
    generateBundle() {
      for (const assetName of liteRtAssetNames) {
        this.emitFile({
          type: 'asset',
          fileName: `litert-wasm/${assetName}`,
          source: readFileSync(join(wasmDirectory, assetName)),
        })
      }
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), liteRtAssets()],
  test: {
    css: true,
    environment: 'jsdom',
    globals: true,
    include: [
      'src/**/*.test.{ts,tsx}',
      'tests/model-compat/**/*.test.{ts,mjs}',
    ],
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      reporter: ['text', 'html', 'json-summary'],
      reportsDirectory: './coverage',
    },
  },
})
