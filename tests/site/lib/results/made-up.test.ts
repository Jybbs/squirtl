import { describe, expect, it } from 'vitest'

import { EPISODES, MADE_UP } from '../../../../docs/.vitepress/lib/results/made-up.ts'
import { AGENTS, groupsOf }  from '../../../../docs/.vitepress/lib/results/results.ts'

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
})
