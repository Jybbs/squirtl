import { describe, expect, it } from 'vitest'

import * as reach from '../../../lib/methods/reach.ts'

/**
 * Rounds each of `values` to three places.
 */
const rounded = (values: readonly number[]): number[] => values.map(value => Number(value.toFixed(3)))

describe('RUN', () => {
  it('carries the deep Q-network’s worth back from the edge a press each time its copy is taken', () => {
    expect([rounded(reach.RUN.online[8]!), rounded(reach.RUN.copy[8]!), reach.RUN.copied])
      .toStrictEqual([[0.009, 0, 0.991, 0.994, 0.997, 1], [0.009, 0.008, 0, 0.994, 0.997, 1], [false, true, false, true, false, true, false, true, false]])
  })

  it('carries PQN’s worth along the whole walk in its first pass', () => {
    expect(rounded(reach.RUN.pqn[1]!)).toStrictEqual([0.121, 0.182, 0.277, 0.423, 0.65, 1])
  })

  it('raises PPO’s odds of Up along the whole walk by the clip a pass, while its critic catches up', () => {
    expect([rounded(reach.RUN.odds[1]!), rounded(reach.RUN.odds[8]!), rounded(reach.RUN.critic[8]!)]).toStrictEqual([
      Array.from({ length: reach.PRESSES }, () => Number((1.2 / reach.ACTIONS).toFixed(3))),
      [0.614, 0.614, 0.614, 0.607, 0.597, 0.587],
      [0.917, 0.928, 0.938, 0.948, 0.958, 0.968]
    ])
  })
})

describe('the loop', () => {
  it('walks Blue up the column a square a press', () => {
    expect([reach.STRIDE.length, reach.STRIDE[0], reach.STRIDE.at(-1)])
      .toStrictEqual([reach.PRESSES * 17, { stance: 'standing', y: 112 }, { stance: 'standing', y: 16 }])
  })

  it('fades in, walks each pass, lands its values under the bubble, and fades out', () => {
    const { end, pass, start, total } = reach.LINE
    expect([0, 8, start, start + 5, start + reach.STRIDE.length, start + pass, end, total - 1].map(at => reach.momentAt(at))).toStrictEqual([
      { bubble: false, fade: 2, landed: 0, pass: 0, walk: -1, where: 'start' },
      { bubble: false, fade: 1, landed: 0, pass: 0, walk: -1, where: 'start' },
      { bubble: false, fade: 0, landed: 0, pass: 1, walk: 0, where: 'start' },
      { bubble: false, fade: 0, landed: 0, pass: 1, walk: 5, where: 'start' },
      { bubble: true, fade: 0, landed: 1, pass: 1, walk: -1, where: 'end' },
      { bubble: false, fade: 0, landed: 1, pass: 2, walk: 0, where: 'start' },
      { bubble: false, fade: 0, landed: 8, pass: 8, walk: -1, where: 'end' },
      { bubble: false, fade: 3, landed: 8, pass: 8, walk: -1, where: 'end' }
    ])
  })

  it('holds a pass at the frame its values land, or before training on Blue’s first square', () => {
    expect([0, 1, reach.PASSES].map(pass => reach.momentAt(reach.clockOf(pass))).map(each => [each.pass, each.landed, each.where]))
      .toStrictEqual([[0, 0, 'start'], [1, 1, 'end'], [8, 8, 'end']])
  })
})

describe('the pad', () => {
  it('reads a value a share of the way between two passes', () => {
    expect(reach.valueAt([[0], [1]], 0.25, 0)).toBe(0.25)
  })

  it('fills Up and the press a network favored before training, or shares PPO’s odds among every other press', () => {
    expect([reach.armsOf(0.5, 1, false), reach.armsOf(0.25, 0, true)]).toStrictEqual([
      { down: 0, left: reach.NOISE[1], right: 0, up: 0.5 },
      { down: 0.125, left: 0.125, right: 0.125, up: 0.25 }
    ])
  })

  it('names each pass', () => {
    expect([reach.passName(0), reach.passName(3)]).toStrictEqual(['Before training', 'After pass 3 of 8'])
  })
})
