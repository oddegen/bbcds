import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { gzipSync } from 'node:zlib'

const distDir = join(process.cwd(), 'dist', 'assets')
const maxInitialJsGzipBytes = 450 * 1024

function collectFiles(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name)

    return entry.isDirectory() ? collectFiles(path) : [path]
  })
}

if (!existsSync(distDir)) {
  throw new Error(
    'dist/assets does not exist. Run pnpm build before check:bundle.',
  )
}

const jsFiles = collectFiles(distDir).filter((file) => file.endsWith('.js'))
const gzipBytes = jsFiles.reduce(
  (total, file) => total + gzipSync(readFileSync(file)).byteLength,
  0,
)

if (gzipBytes > maxInitialJsGzipBytes) {
  throw new Error(
    `Initial JS gzip size ${gzipBytes} exceeds budget ${maxInitialJsGzipBytes}.`,
  )
}

console.log(`Initial JS gzip size ${gzipBytes} bytes is within budget.`)
