import { describe, expect, it } from 'vitest'

import * as results from '../../../lib/results/results.ts'

/**
 * Two runs of the deep Q-network trained along the curriculum, one evaluated
 * twice and one once, beside one run of PPO trained without it.
 */
const RESULTS: results.Results = {
  comparisons: [
    {
      agent      : 'dqn',
      baseline   : { interval: [0, 0.25], runs: [2], value: 0.125 },
      beats      : { interval: [0.5, 1], runs: [2, 2], value: 0.75 },
      curriculum : true,
      reached    : { interval: [0.5, 1], runs: [2], value: 0.75 }
    },
    {
      agent      : 'ppo',
      baseline   : { interval: null, runs: [1], value: 0 },
      beats      : { interval: null, runs: [1, 1], value: 0.5 },
      curriculum : false,
      reached    : { interval: null, runs: [1], value: 0.5 }
    }
  ],
  runs: [
    {
      agent      : 'dqn',
      baseline   : { reached: 0.25, reward: 1, step: null },
      curriculum : true,
      name       : 'dqn-a',
      scores     : [{ reached: 0.5, reward: 2, step: 500 }, { reached: 1, reward: 4, step: 1000 }],
      seed       : 0
    },
    {
      agent      : 'dqn',
      baseline   : { reached: 0, reward: 0, step: null },
      curriculum : true,
      name       : 'dqn-b',
      scores     : [{ reached: 0.5, reward: 3, step: 500 }],
      seed       : 1
    },
    {
      agent      : 'ppo',
      baseline   : { reached: 0, reward: 0, step: null },
      curriculum : false,
      name       : 'ppo-a',
      scores     : [{ reached: 0.5, reward: 1, step: 1000 }],
      seed       : 0
    }
  ]
}

/**
 * The groups of the results above.
 */
const GROUPS = results.groupsOf(RESULTS)

describe('groupsOf', () => {
  it('pairs each comparison with its runs under its agent’s name, naming the curriculum where it trained along one', () => {
    expect(GROUPS.map(group => [group.name, group.runs.map(run => run.name)])).toStrictEqual([
      ['Deep Q-network, curriculum', ['dqn-a', 'dqn-b']],
      ['PPO', ['ppo-a']]
    ])
  })

  it('reads the runs the repository commits by default', () => {
    expect(results.groupsOf()).toStrictEqual(results.groupsOf(results.COMMITTED))
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

describe('keyOf', () => {
  it('sets the agent’s share reaching the starter beside the baseline’s and the chance a run beats it', () => {
    expect(results.keyOf(GROUPS[0]!)).toStrictEqual([
      { figures: ['0.75 [0.50, 1.00] over 2', ''], name: 'Deep Q-network, curriculum', role: 'agent' },
      { figures: ['0.13 [0.00, 0.25] over 2', '0.75 [0.50, 1.00] over 2 and 2'], name: 'Random presses', role: 'random' }
    ])
  })
})

describe('curvesOf', () => {
  const curves = results.curvesOf(GROUPS[0]!, 288, 640)

  it('draws each run’s line across the steps up to the run that trained longest', () => {
    expect([curves.last, curves.lines]).toStrictEqual([1000, ['M336,126L624,12', 'M336,126']])
  })

  it('sets the baseline’s level line at its interquartile mean', () => {
    expect(curves.baseline).toBe(211.5)
  })

  it('labels each share along the side and the first and last step along the bottom', () => {
    expect(curves.labels.map(label => label.text)).toStrictEqual(['0%', '25%', '50%', '75%', '100%', '0', '1,000'])
  })
})

describe('comparisonOf', () => {
  const strip = results.comparisonOf(GROUPS, 640)

  it('takes a row for each group beneath the room the strip leaves at its top and bottom', () => {
    expect([strip.height, strip.rows.map(row => row.name.text)]).toStrictEqual([156, ['Deep Q-network, curriculum', 'PPO']])
  })

  it('sets each run’s dot at its share and the mean across its interval', () => {
    expect(strip.rows[0]!.agent).toStrictEqual({ dots: [624, 384], interval: [384, 624], mean: 504, y: 28 })
  })

  it('draws no interval for a sample of one run', () => {
    expect(strip.rows[1]!.agent).toStrictEqual({ dots: [384], interval: null, mean: 384, y: 76 })
  })
})
