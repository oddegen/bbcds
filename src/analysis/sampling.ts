import type { AnalysisDecision, ModelMode } from './types'

export const RISK_THRESHOLD = 0.43
export const MAX_ANCHOR_SAMPLES = 24
export const MAX_TOTAL_SAMPLES = 28
export const ANALYSIS_TIMEOUT_MS = 90_000

const TARGET_INTERVAL_SECONDS = 10
const END_EPSILON_SECONDS = 0.05
const TIME_DEDUPLICATION_EPSILON = 0.01
const REFINEMENT_OFFSETS = [-1, 1, -2, 2] as const

function lastDecodableTime(durationSeconds: number): number {
  return Math.max(
    0,
    durationSeconds - Math.min(END_EPSILON_SECONDS, durationSeconds / 2),
  )
}

export function createAnchorTimes(durationSeconds: number): number[] {
  if (!Number.isFinite(durationSeconds) || durationSeconds <= 0) {
    throw new Error('Video duration must be a positive finite number')
  }

  const count = Math.min(
    MAX_ANCHOR_SAMPLES,
    Math.max(2, Math.ceil(durationSeconds / TARGET_INTERVAL_SECONDS) + 1),
  )
  const end = lastDecodableTime(durationSeconds)

  return Array.from({ length: count }, (_, index) =>
    index === count - 1 ? end : (end * index) / (count - 1),
  )
}

function includesNearby(times: readonly number[], candidate: number): boolean {
  return times.some(
    (time) => Math.abs(time - candidate) < TIME_DEDUPLICATION_EPSILON,
  )
}

export function createRefinementTimes(
  anchorSeconds: number,
  durationSeconds: number,
  existingTimes: readonly number[],
): number[] {
  const end = lastDecodableTime(durationSeconds)
  const refinements: number[] = []

  for (const offset of REFINEMENT_OFFSETS) {
    const candidate = Math.min(end, Math.max(0, anchorSeconds + offset))
    if (
      !includesNearby(existingTimes, candidate) &&
      !includesNearby(refinements, candidate)
    ) {
      refinements.push(candidate)
    }
  }

  return refinements.slice(0, MAX_TOTAL_SAMPLES - existingTimes.length)
}

export interface DecisionInput {
  modelMode: ModelMode
  risks: readonly number[]
  anchorsComplete: boolean
  timedOut: boolean
}

export interface DecisionResult {
  decision: AnalysisDecision
  confidence?: number
  reason?: 'unconfirmed' | 'timeout'
}

export function decideAnalysis(input: DecisionInput): DecisionResult | null {
  if (input.timedOut) {
    return { decision: 'inconclusive', reason: 'timeout' }
  }

  if (input.modelMode === 'demo') {
    return input.anchorsComplete ? { decision: 'demo' } : null
  }

  const positives = input.risks.filter((risk) => risk >= RISK_THRESHOLD)
  if (positives.length >= 2) {
    const strongest = positives
      .toSorted((left, right) => right - left)
      .slice(0, 2)
    const first = strongest[0]
    const second = strongest[1]
    if (first === undefined || second === undefined) {
      throw new Error('Confirmed evidence is missing risk values')
    }
    return {
      decision: 'sensitive',
      confidence: (first + second) / 2,
    }
  }

  if (!input.anchorsComplete) return null

  if (positives.length === 1) {
    return { decision: 'inconclusive', reason: 'unconfirmed' }
  }

  const maximumRisk = input.risks.reduce(
    (maximum, risk) => Math.max(maximum, risk),
    0,
  )
  return { decision: 'safe', confidence: 1 - maximumRisk }
}
