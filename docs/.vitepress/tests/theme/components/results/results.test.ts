// @vitest-environment happy-dom
import { enableAutoUnmount, mount }            from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { nextTick }                            from 'vue'

import type * as results from '../../../../lib/results/results.ts'

/**
 * Whether the stand-in below holds the committed runs, which hold none, or two
 * runs of two groups, beside those two runs, the second group's estimates
 * taking no interval as a group of one run does.
 */
const { held, standIn } = vi.hoisted(() => {
  const estimate = { interval: [0, 1] as const, runs: [1], value: 0.5 }
  const single   = { ...estimate, interval: null }
  const trained  = { baseline: { reached: 0, reward: 0, step: null }, scores: [{ reached: 0.5, reward: 0, step: 100 }], seed: 0 }
  return {
    held    : { runs: false },
    standIn : {
      comparisons : [
        { agent: 'dqn', baseline: estimate, beats: estimate, curriculum: false, reached: estimate },
        { agent: 'pqn', baseline: single, beats: single, curriculum: true, reached: single }
      ],
      runs : [
        { ...trained, agent: 'dqn', curriculum: false, name: 'dqn' },
        { ...trained, agent: 'pqn', curriculum: true, name: 'pqn' }
      ]
    } satisfies results.Results
  }
})

vi.mock('../../../../lib/results/results.ts', async original => {
  const module = await original<typeof import('../../../../lib/results/results.ts')>()
  return { ...module, groupsOf: () => module.groupsOf(held.runs ? standIn : module.COMMITTED) }
})

const { ResultsComparison } = await import('../../../../theme/components/results/comparison.tsx')
const { ResultsCurves }     = await import('../../../../theme/components/results/curves.tsx')

enableAutoUnmount(afterEach)

describe.each([ResultsComparison, ResultsCurves])('$name', widget => {
  it('draws nothing until a run is committed', () => {
    held.runs = false
    expect(mount(widget).html()).toBe('')
  })
})

describe('ResultsCurves', () => {
  it('draws the group a press on its key picks, its runs’ lines beside the baseline’s level line', async () => {
    held.runs = true
    const wrapper = mount(ResultsCurves)
    const picked  = () => wrapper.findAll('[aria-pressed="true"]').map(entry => entry.text())

    expect([picked(), wrapper.findAll('path').length]).toStrictEqual([['Deep Q-network'], 3])

    await wrapper.findAll('button')[1]!.trigger('click')
    await nextTick()

    expect(picked()).toStrictEqual(['PQN, curriculum'])
  })
})

describe('ResultsComparison', () => {
  it('draws a row for each group, a dot for each run beside its baseline, and a whisker only where a bootstrap interval exists', () => {
    held.runs = true
    const wrapper = mount(ResultsComparison)

    expect([wrapper.findAll('circle').length, wrapper.findAll('path').length, wrapper.text()]).toStrictEqual([
      4, 7, '0%25%50%75%100%Deep Q-networkPQN, curriculum'
    ])
  })
})
