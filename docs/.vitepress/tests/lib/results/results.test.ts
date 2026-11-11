import { describe, expect, it } from 'vitest'

import * as results from '../../../lib/results/results.ts'
import FIXTURE      from './fixtures/results.json' with { type: 'json' }

/**
 * Seven runs across every agent and both starts, PQN's estimates taking no
 * interval as a group of one run does, beside random presses' share across
 * every run.
 */
const RESULTS = FIXTURE as unknown as results.Results

/**
 * The groups of the runs above, in the order their comparisons stand.
 */
const GROUPS = results.groupsOf(RESULTS)

describe('groupsOf', () => {
  it('pairs each comparison with its runs under its agent’s name and hue, naming the curriculum where it trained along one', () => {
    expect(GROUPS.map(group => [group.id, group.name, group.hue, group.runs.map(run => run.seed)])).toStrictEqual([
      ['dqn-bedroom', 'Deep Q-network', 'fern', [1]],
      ['ppo-bedroom', 'PPO', 'denim', [2, 3]],
      ['ppo-curriculum', 'PPO, curriculum', 'denim', [4, 5]],
      ['pqn-bedroom', 'PQN', 'heath', [6]],
      ['pqn-curriculum', 'PQN, curriculum', 'heath', [7]]
    ])
  })

  it('reads the runs the repository commits by default', () => {
    expect(results.groupsOf()).toStrictEqual(results.groupsOf(results.COMMITTED))
  })
})

describe('interquartile', () => {
  it.each([
    [[4, 1, 100, 3, 2], 3],
    [[0.5, 0.25], 0.375],
    [[7], 7]
  ])('takes the mean of %j inside its quartiles as %d', (values, mean) => {
    expect(results.interquartile(values)).toBe(mean)
  })
})

describe('meansOf', () => {
  it('takes the interquartile mean across a group’s runs at each evaluation', () => {
    expect(results.meansOf(GROUPS[1]!)).toStrictEqual([
      { reached: 0.375, reward: 0.75, step: 500_000 },
      { reached: 0.875, reward: 1.75, step: 1_000_000 },
      { reached: 1, reward: 2, step: 1_500_000 }
    ])
  })

  it('takes each later evaluation across the runs that reached it', () => {
    const [first, second] = GROUPS[1]!.runs
    const short           = { ...GROUPS[1]!, runs: [first!, { ...second!, scores: second!.scores.slice(0, 1) }] }

    expect(results.meansOf(short).map(score => score.reached)).toStrictEqual([0.375, 1, 1])
  })
})

describe('spelled', () => {
  it.each([
    [{ interval: [0.5, 1], runs: [5], value: 0.75 }, '0.75 [0.50, 1.00] over 5'],
    [{ interval: null, runs: [1, 1], value: 0.5 }, '0.50 over 1 and 1']
  ] as const)('spells %j as %s', (estimate, text) => {
    expect(results.spelled(estimate)).toBe(text)
  })
})

describe('percent', () => {
  it.each([
    [{ interval: [0.9, 1], runs: [2], value: 1 }, '100% [90, 100]'],
    [{ interval: null, runs: [1], value: 0.4 }, '40%']
  ] as const)('spells %j as %s', (estimate, text) => {
    expect(results.percent(estimate)).toBe(text)
  })
})

describe('verdictOf', () => {
  it.each([
    [[0.6, 1], 'above'],
    [[0, 0.3], 'below'],
    [[0.25, 0.75], 'even'],
    [[0.5, 0.9], 'even'],
    [[0.1, 0.5], 'even'],
    [null, 'even']
  ] as const)('reads odds across %j as %s', (interval, verdict) => {
    expect(results.verdictOf({ interval, runs: [2, 2], value: 0.5 })).toBe(verdict)
  })
})

describe('figuresOf', () => {
  it('lists each group’s share and odds against random presses, lit in its hue while pressed, above random presses’ share', () => {
    const entries = results.figuresOf(GROUPS, RESULTS.random!, new Set(['ppo-bedroom']))

    expect(entries.map(entry => [entry.name, entry.figures])).toStrictEqual([
      ['Deep Q-network', ['0.00 over 1', '0.10 [0.00, 0.30] over 1 and 1']],
      ['PPO', ['1.00 [0.90, 1.00] over 2', '1.00 [0.75, 1.00] over 2 and 2']],
      ['PPO, curriculum', ['1.00 [1.00, 1.00] over 2', '0.90 [0.60, 1.00] over 2 and 2']],
      ['PQN', ['0.40 over 1', '0.50 over 1 and 1']],
      ['PQN, curriculum', ['0.80 over 1', '0.50 over 1 and 1']],
      ['Random presses', ['0.10 [0.00, 0.25] over 7', '']]
    ])
    expect(entries.map(entry => entry.hue)).toStrictEqual([null, 'denim', null, null, null, undefined])
  })
})
