import {
  createAnchorTimes,
  createRefinementTimes,
  decideAnalysis,
  MAX_ANCHOR_SAMPLES,
} from './sampling'

describe('video sampling policy', () => {
  it('covers short and long videos with bounded anchors', () => {
    expect(createAnchorTimes(2)).toHaveLength(2)

    const longVideo = createAnchorTimes(3600)
    expect(longVideo).toHaveLength(MAX_ANCHOR_SAMPLES)
    expect(longVideo[0]).toBe(0)
    expect(longVideo.at(-1)).toBeCloseTo(3599.95)
  })

  it('adds unique bounded refinements around an elevated anchor', () => {
    expect(createRefinementTimes(5, 20, [0, 5, 19.95])).toEqual([4, 6, 3, 7])
    expect(createRefinementTimes(0, 2, [0, 1.95])).toEqual([1])
  })

  it('requires confirmation before returning a sensitive result', () => {
    expect(
      decideAnalysis({
        modelMode: 'approved',
        risks: [0.8],
        anchorsComplete: true,
        timedOut: false,
      }),
    ).toEqual({ decision: 'inconclusive', reason: 'unconfirmed' })

    expect(
      decideAnalysis({
        modelMode: 'approved',
        risks: [0.8, 0.6],
        anchorsComplete: false,
        timedOut: false,
      }),
    ).toEqual({ decision: 'sensitive', confidence: 0.7 })
  })

  it('returns safe only after complete coverage and keeps confidence heuristic', () => {
    expect(
      decideAnalysis({
        modelMode: 'approved',
        risks: [0.1, 0.2],
        anchorsComplete: false,
        timedOut: false,
      }),
    ).toBeNull()
    expect(
      decideAnalysis({
        modelMode: 'approved',
        risks: [0.1, 0.2],
        anchorsComplete: true,
        timedOut: false,
      }),
    ).toEqual({ decision: 'safe', confidence: 0.8 })
  })

  it('never turns demo completion or timeout into a safety decision', () => {
    expect(
      decideAnalysis({
        modelMode: 'demo',
        risks: [0],
        anchorsComplete: true,
        timedOut: false,
      }),
    ).toEqual({ decision: 'demo' })
    expect(
      decideAnalysis({
        modelMode: 'demo',
        risks: [],
        anchorsComplete: false,
        timedOut: true,
      }),
    ).toEqual({ decision: 'inconclusive', reason: 'timeout' })
  })
})
