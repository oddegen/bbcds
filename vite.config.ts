import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
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
