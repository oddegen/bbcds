import { existsSync, readdirSync } from 'node:fs'
import { join } from 'node:path'

const modelDir = join(process.cwd(), 'public', 'models')

if (!existsSync(modelDir)) {
  console.log('No model assets present.')
  process.exit(0)
}

const files = readdirSync(modelDir, { recursive: true })

if (files.length === 0) {
  console.log('Model asset directory exists but is empty.')
  process.exit(0)
}

throw new Error(
  'Model assets require an ADR and benchmark evidence before committing model files.',
)
