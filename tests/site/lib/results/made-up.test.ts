import { describe, expect, it } from 'vitest'

import { EPISODES, MADE_UP }               from '../../../../docs/.vitepress/lib/results/made-up.ts'
import { AGENTS, groupsOf, interquartile } from '../../../../docs/.vitepress/lib/results/results.ts'

describe('MADE_UP', () => {
  it('holds a bedroom group for each agent in the order the charts declare them, each of five seeds', () => {
    expect(groupsOf(MADE_UP).map(group => [group.agent, group.curriculum, group.runs.length]))
      .toStrictEqual(Object.keys(AGENTS).map(agent => [agent, false, 5]))
  })

  it('ends each run on a whole count of its episodes, random presses’ share under each seed too', () => {
    const counts = MADE_UP.runs.map(run => run.scores.at(-1)!.reached * EPISODES)

    expect(counts.every(count => Number.isInteger(count))).toBe(true)
    expect(MADE_UP.runs.every(run => run.baseline.reached * EPISODES % 1 === 0)).toBe(true)
    expect(MADE_UP.random!.interval![0]).toBeLessThan(MADE_UP.random!.value)
  })

  it('gives each agent the odds of beating random presses its reached share sets', () => {
    expect(MADE_UP.comparisons.map(comparison => [comparison.agent, comparison.beats.value]))
      .toStrictEqual([['ppo', 0.96], ['pqn', 0.88], ['dqn', 0.04]])
  })

  it('ends each run on a share its comparison takes the interquartile mean of', () => {
    expect(groupsOf(MADE_UP).map(group => group.comparison.reached.value)).toStrictEqual(groupsOf(MADE_UP)
      .map(group => interquartile(group.runs.map(run => run.scores.at(-1)!.reached))))
  })
})
