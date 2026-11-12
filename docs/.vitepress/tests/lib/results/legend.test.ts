import { describe, expect, it } from 'vitest'

import { CURVES, SAMPLE, legendOf, lookOf } from '../../../lib/results/legend.ts'
import * as results                         from '../../../lib/results/results.ts'
import FIXTURE                              from './fixtures/results.json' with { type: 'json' }

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
      ['Share reaching the starter', ['None', 'Up to 33%', 'Up to 67%', 'Above 67%']],
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

describe('lookOf', () => {
  it('sets the curves’ key after what each start draws, every other row the legend’s', () => {
    const legend = legendOf(GROUPS, RESULTS.random!, 'hatch')

    expect(lookOf(GROUPS, RESULTS.random!, 'hatch'))
      .toStrictEqual([legend[0], legend[1], { entries: CURVES, head: 'Curve' }, ...legend.slice(2)])
  })
})

describe('SAMPLE', () => {
  it('holds one made-up group for each agent, so a look drawn on it names every agent', () => {
    const [agents] = lookOf(SAMPLE.groups, SAMPLE.random, 'hatch')

    expect(agents!.entries.map(entry => entry.name).toSorted())
      .toStrictEqual(Object.values(results.AGENTS).map(agent => agent.short).toSorted())
  })
})
