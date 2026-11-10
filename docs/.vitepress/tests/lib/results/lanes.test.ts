import { describe, expect, it } from 'vitest'

import * as lanes   from '../../../lib/results/lanes.ts'
import * as results from '../../../lib/results/results.ts'
import FIXTURE      from './fixtures/results.json' with { type: 'json' }

/**
 * The groups of the seven runs the fixture holds.
 */
const GROUPS = results.groupsOf(FIXTURE as unknown as results.Results)

describe('shadeOf', () => {
  it.each([
    [0, 0],
    [0.2, 1],
    [1 / 3, 1],
    [0.5, 2],
    [2 / 3, 2],
    [0.8, 3],
    [1, 3]
  ])('shades a share of %d as %d', (share, shade) => {
    expect(lanes.shadeOf(share)).toBe(shade)
  })
})

describe('finalsWidth', () => {
  it.each([
    [null, 247],
    ['finals', 428],
    ['curves', lanes.LANES.tab]
  ] as const)('gives the last evaluation of a figure 688 pixels wide, %s widened, %d pixels', (side, width) => {
    expect(lanes.finalsWidth(688, side)).toBe(width)
  })
})

describe('oddsLine', () => {
  it.each([
    ['random', [0.6, 1], 'above', 'BEATS'],
    ['random', [0, 0.3], 'below', 'BELOW'],
    ['random', null, 'even', 'NOT CLEAR'],
    ['bedroom', [0.55, 0.9], 'above', 'BETTER'],
    ['bedroom', [0.1, 0.4], 'below', 'WORSE'],
    ['bedroom', [0.25, 0.75], 'even', 'NOT CLEAR']
  ] as const)('reads odds against %s across %j as %s, worded %s', (against, interval, verdict, word) => {
    const line = lanes.oddsLine({ interval, runs: [2, 2], value: 0.5 }, against, 10, 20)

    expect([line.label.text, line.verdict, line.word.text]).toStrictEqual([`VS ${against.toUpperCase()}`, verdict, word])
  })
})

describe('oddsOf', () => {
  it('places the odds, their interval, and even odds along a track from 0 to 100%', () => {
    expect(lanes.oddsOf({ interval: [0.25, 0.75], runs: [2, 2], value: 0.6 }, 100, 8, 40)).toStrictEqual({
      at: 124, even: 120, interval: [110, 130], wide: 40, x: 100, y: 8
    })
  })

  it('places no interval where the estimate holds none', () => {
    expect(lanes.oddsOf({ interval: null, runs: [1, 1], value: 0.5 }, 0, 0, 40).interval).toBeNull()
  })
})

describe('laneHeight', () => {
  it('holds a lane at its least height until its seeds’ rows run taller', () => {
    const seeds = { ...GROUPS[1]!, runs: Array.from({ length: 6 }, () => GROUPS[1]!.runs[0]!) }

    expect([lanes.laneHeight(GROUPS), lanes.laneHeight([seeds])]).toStrictEqual([lanes.LANES.lane, 54.5])
  })
})
