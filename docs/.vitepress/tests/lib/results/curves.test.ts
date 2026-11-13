// @vitest-environment happy-dom
import { enableAutoUnmount, mount }        from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { defineComponent, ref }            from 'vue'

import { curvesOf, useCurves } from '../../../lib/results/curves.ts'
import * as results            from '../../../lib/results/results.ts'
import FIXTURE                 from './fixtures/results.json' with { type: 'json' }

enableAutoUnmount(afterEach)

/**
 * The groups of the seven runs the fixture holds.
 */
const GROUPS = results.groupsOf(FIXTURE as unknown as results.Results)

describe('curvesOf', () => {
  const curves = curvesOf(GROUPS, 0.1, 288, 640)

  it('draws a curve a group through the mean at each evaluation, dashed along the curriculum', () => {
    expect(curves.lines.map(line => [line.group.id, line.dashed, line.points.length])).toStrictEqual([
      ['dqn-bedroom', false, 3],
      ['ppo-bedroom', false, 3],
      ['ppo-curriculum', true, 3],
      ['pqn-bedroom', false, 3],
      ['pqn-curriculum', true, 3]
    ])
  })

  it('places each mean at its share and its step, random presses’ level line at its share', () => {
    const { frame } = curves
    const [, ppo]   = curves.lines

    expect([ppo!.points, curves.baseline]).toStrictEqual([
      results.meansOf(GROUPS[1]!).map(score => [frame.x(score.step, 1_500_000), frame.y(score.reached, 1)]),
      frame.y(0.1, 1)
    ])
  })

  it('labels the shares and the steps in millions, titling each axis with its variable and unit', () => {
    expect([...curves.labels, ...curves.titles].map(label => label.text)).toStrictEqual([
      '0%', '25%', '50%', '75%', '100%', '0', '0.5', '1', '1.5', 'Environment steps (millions)', 'Episodes reaching the goal (%)'
    ])
  })
})

describe('useCurves', () => {
  it('draws the runs it is handed in place of the committed ones', () => {
    let drawn: readonly results.Group[] = []
    mount(defineComponent({ setup: () => { drawn = useCurves(ref(), FIXTURE as unknown as results.Results).groups; return () => null } }))

    expect(drawn).toStrictEqual(GROUPS)
  })
})
