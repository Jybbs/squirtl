import { describe, expect, it } from 'vitest'

import { legendOf } from '../../../lib/results/legend.ts'
import * as results from '../../../lib/results/results.ts'
import FIXTURE      from './fixtures/results.json' with { type: 'json' }

/**
 * The seven runs the fixture holds and their groups.
 */
const RESULTS = FIXTURE as unknown as results.Results
const GROUPS  = results.groupsOf(RESULTS)

describe('legendOf', () => {
  const legend = legendOf(GROUPS, RESULTS.random!, 'hatch')

  it('heads each row with what its marks decode', () => {
    expect(legend.map(row => [row.head, row.entries.map(entry => entry.name)])).toStrictEqual([
      ['Agent', ['DQN', 'PPO', 'PQN']],
      ['Start', ['From the bedroom', 'With the curriculum']],
      ['Share reaching the goal', ['None', 'Up to 33%', 'Up to 67%', 'Above 67%']],
      ['Last evaluation', ['A seed, from its random share', 'Interquartile mean, 95% interval']],
      ['Random presses', ['Across every seed']],
      ['Verdict', ['Odds of the higher return, 95% interval', 'Even odds']]
    ])
  })

  it('draws each agent in its hue, hatches the curriculum through the pattern named, and states random presses’ share', () => {
    const [agents, starts, , , random] = legend

    expect([
      agents!.entries.map(entry => entry.hue),
      starts!.entries.map(entry => entry.mark!.includes('url(#hatch)')),
      random!.entries[0]!.value
    ]).toStrictEqual([['fern', 'denim', 'heath'], [false, true], '10% [0, 25]'])
  })
})
