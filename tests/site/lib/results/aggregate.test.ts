import { describe, expect, it } from 'vitest'

import * as aggregate   from '../../../../docs/.vitepress/lib/results/aggregate.ts'
import type { Results } from '../../../../docs/.vitepress/lib/results/results.ts'
import FIXTURE          from './fixtures/results.json' with { type: 'json' }

/**
 * Four shares a bootstrap draws from, spanning the lowest share to the
 * highest.
 */
const SHARES = [0, 0.25, 0.5, 1]
/**
 * The aggregate of each group the fixture's seven runs fall into.
 */
const aggregates = aggregate.aggregatesOf(FIXTURE as unknown as Results)
/**
 * The aggregate of each group the repository commits, five runs apiece under
 * seeds 1 to 5.
 */
const committed = aggregate.aggregatesOf()

describe('aggregatesOf', () => {
  it('reads every group beside its interquartile mean and random presses’ under its seeds', () => {
    expect(aggregates.map(each => [each.group.id, each.reached.value, each.random.value])).toStrictEqual([
      ['dqn-bedroom', 0, 0],
      ['ppo-bedroom', 1, 0.125],
      ['ppo-curriculum', 1, 0.125],
      ['pqn-bedroom', 0.4, 0],
      ['pqn-curriculum', 0.8, 0]
    ])
  })

  it('reads the runs the repository commits by default', () => {
    expect(committed).toHaveLength(5)
  })
})

describe('pairedOf', () => {
  it('reads each run in the order of its seed beside random presses’ share under it', () => {
    expect(aggregate.pairedOf(aggregates[1]!)).toStrictEqual([
      { episodes: 8, random: 0.25, seed: 2, share: 1 },
      { episodes: 8, random: 0, seed: 3, share: 1 }
    ])
  })
})

describe('the bootstrap', () => {
  it('reads the middle 95% of [4, 1, 2, 3] as NumPy’s percentiles read it, interpolating linearly', () => {
    expect(aggregate.middleOf([4, 1, 2, 3]).map(bound => bound.toFixed(3))).toStrictEqual(['1.075', '3.925'])
  })

  it('draws the same means each time from one seed', () => {
    expect(aggregate.drawnOf(SHARES, 200)).toStrictEqual(aggregate.drawnOf(SHARES, 200))
  })

  it('draws only means the shares reach, from the lowest to the highest', () => {
    const drawn = aggregate.drawnOf(SHARES, 200)
    expect([drawn.length, Math.min(...drawn), Math.max(...drawn)]).toStrictEqual([200, 0, 1])
  })

  it('draws other means from another seed', () => {
    expect(aggregate.drawnOf(SHARES, 200, 1)).not.toStrictEqual(aggregate.drawnOf(SHARES, 200))
  })

  it('draws 9,999 times by default, as SciPy’s bootstrap does', () => {
    expect(aggregate.drawnOf([0, 1])).toHaveLength(aggregate.RESAMPLES)
  })

  it.each([
    ['one share', [0.4], { interval: null, runs: [1], value: 0.4 }],
    ['equal shares', [0.25, 0.25, 0.25], { interval: [0.25, 0.25], runs: [3], value: 0.25 }]
  ])('estimates %s itself', (_, shares, estimate) => {
    expect(aggregate.estimateOf(shares, 90)).toStrictEqual(estimate)
  })

  it.each([
    ['every episode', [1, 1, 1], [0.025 ** (1 / 90), 1]],
    ['no episode', [0, 0], [0, 1 - 0.025 ** (1 / 60)]]
  ])('bounds a share reaching the goal in %s by the exact binomial interval', (_, shares, interval) => {
    expect(aggregate.exactOf(shares, shares.length * 30)).toStrictEqual(interval)
  })

  it.each([[[1, 0.9, 1]], [[0.5, 0.5]], [[]]])('leaves %j to the bootstrap', shares => {
    expect(aggregate.exactOf(shares, 90)).toBeNull()
  })

  it('bounds 150 episodes of every run reaching the goal from 97.6% as SciPy’s binomial test does', () => {
    expect(aggregate.exactOf(Array.from({ length: 5 }, () => 1), 150)![0]).toBeCloseTo(0.97571, 5)
  })

  it('draws random presses’ interval over every committed seed within two points of SciPy’s', () => {
    const shares = aggregate.pairedOf(committed[0]!).map(run => run.random)
    const drawn  = aggregate.estimateOf(shares).interval!
    expect(aggregate.gapOf(drawn, aggregate.spanOf(committed[0]!.random))).toBeLessThanOrEqual(2)
  })
})

describe('the spelled figures', () => {
  it('spells a share, an interval’s span, and the gap between two intervals in whole points', () => {
    expect([
      aggregate.percentOf(0.125),
      aggregate.spanOf(aggregates[3]!.reached),
      aggregate.spanOf(aggregates[1]!.reached),
      aggregate.gapOf([0.1, 0.5], [0.16, 0.46])
    ]).toStrictEqual(['13%', [0.4, 0.4], [0.9, 1], 6])
  })

  it.each([
    [
      0,
      'DQN',
        'Deep Q-network (DQN), from the bedroom: interquartile mean 0% over 1 run, '
      + 'beside random presses under the same seeds at 0%'
    ],
    [
      2,
      'PPO along the curriculum',
        'PPO, with the curriculum: interquartile mean 100%, 95% interval 100 to 100% over 2 runs, '
      + 'beside random presses under the same seeds at 13%, 95% interval 0 to 25%'
    ]
  ])('names group %d in a sentence as %j and to a screen reader as %j', (n, who, spoken) => {
    expect([aggregate.whoOf(aggregates[n]!), aggregate.spokenOf(aggregates[n]!)]).toStrictEqual([who, spoken])
  })
})
