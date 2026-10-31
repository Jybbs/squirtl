// @vitest-environment happy-dom
import { enableAutoUnmount, mount }        from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { defineComponent, h, ref }         from 'vue'

import * as climb   from '../../../../lib/front/reward/climb.ts'
import { traceOf }  from '../../../../lib/front/reward.ts'
import { stubSize } from '../../../common/browser.ts'

/**
 * Every step of the default episode, recorded once for every case.
 */
const TRACE = traceOf()

/**
 * The climb drawn beside a screen 401 pixels wide, as tall as the screen.
 */
const PLOT = climb.climbOf(TRACE, 401, 298)

/**
 * Mounts a box drawing the climb through `useClimb`, the browser's
 * `ResizeObserver` stood in for by one that reports the size a case gives it,
 * and returns the call that resizes the box beside the drawing it reads.
 */
function measured() {
  const resize = stubSize()
  let plot!: ReturnType<typeof climb.useClimb>
  mount(defineComponent({
    setup: () => {
      const box = ref<HTMLElement>()
      plot      = climb.useClimb(box, TRACE)
      return () => h('div', { ref: box })
    }
  }), { attachTo: document.body })
  return { plot, resize }
}

enableAutoUnmount(afterEach)

describe('climbOf', () => {
  it('runs the course from the floor at the first step to the starter near the top, a step at a time', () => {
    expect([PLOT.heads[0], PLOT.heads.at(-1), PLOT.heads.length]).toStrictEqual([[48, 298], [369, 25.3], 164])
    expect(PLOT.course).toMatch(/^M48,298H50V298H51\.9V297\.9.*H369V25\.3$/u)
  })

  it('draws the axis with a tick at each value it labels, and a tick on the floor per new position', () => {
    expect(PLOT.axis).toBe('M47.5,-6V298.5H369M43,298H48M43,149H48M43,0H48')
    expect(PLOT.rug.match(/M/gu)).toHaveLength(60)
    expect(PLOT.values).toStrictEqual([
      { anchor: 'end', text: '0.00', x: 38, y: 302 },
      { anchor: 'end', text: '0.50', x: 38, y: 153 },
      { anchor: 'end', text: '1.00', x: 38, y: 4 }
    ])
  })

  it('sets each jump’s tile and mark beside its dot', () => {
    expect(PLOT.jumps.map(jump => [jump.at, jump.term, jump.dot, jump.tile, jump.mark])).toStrictEqual([
      [131, 'milestone', [306, 265.3], [272, 254.3], [275, 257.3]],
      [156, 'milestone', [355.2, 234.1], [321.2, 223.1], [324.2, 226.1]],
      [156, 'milestone', [355.2, 204.3], [321.2, 193.3], [324.2, 196.3]],
      [163, 'starter', [369, 25.3], [335, 14.3], [338, 17.3]]
    ])
  })

  it.each([
    [401, ['0', '50', '100']],
    [700, ['0', '25', '50', '75', '100', '125', '150']]
  ])('labels the steps at %i pixels, leaving out a label the axis’s title would meet', (width, labels) => {
    const plot = climb.climbOf(TRACE, width, 300)

    expect(plot.steps.map(label => [label.anchor, label.text])).toStrictEqual(labels.map(text => ['middle', text]))
    expect(plot.title).toStrictEqual({ anchor: 'end', text: 'Step', x: width - 32, y: 320 })
  })

  it('draws at the tuning it is given', () => {
    const plot = climb.climbOf(TRACE, 401, 298, { ...climb.CLIMB, ticks: [0, 1], title: 0 })

    expect([plot.values.map(label => label.text), plot.steps.at(-1)!.text])
      .toStrictEqual([['0.00', '1.00'], '150'])
  })
})

describe('useClimb', () => {
  it('draws nothing before the box is measured, then the climb at its size, never under the least', () => {
    const { plot, resize } = measured()
    const before           = plot.value
    const sized            = () => [plot.value?.width, plot.value?.height]

    resize(100, 50)
    const least = sized()
    resize(401.4, 297.8)

    expect([before, least, sized()]).toStrictEqual([null, [240, 120], [401, 298]])
  })

  it('keeps the drawing while the box keeps its size', () => {
    const { plot, resize } = measured()

    resize(401, 298)
    const first = plot.value
    resize(401.2, 298.3)

    expect(plot.value).toBe(first)
  })
})
