// @vitest-environment happy-dom
import { enableAutoUnmount, mount }          from '@vue/test-utils'
import { afterEach, describe, expect, it }   from 'vitest'
import { defineComponent, h, nextTick, ref } from 'vue'

import * as chart from '../../../../lib/front/race/chart.ts'
import * as race  from '../../../../lib/front/race.ts'

/**
 * A race of three episodes each, the agent reaching the starter at steps 10 and
 * 100 and missing once, random presses never reaching it.
 */
const RACE: race.Race = {
  agent  : [{ reached: true, steps: 100 }, { reached: false, steps: 10240 }, { reached: true, steps: 10 }],
  random : Array.from({ length: 3 }, () => ({ reached: false, steps: 10240 }))
}

/**
 * The evaluation behind the race above, three episodes on a clock of four
 * stops.
 */
const EVALUATING: race.Evaluating = { ...race.EVALUATING, episodes: 3, stops: 4 }

/**
 * The race above drawn at 640 pixels under the evaluation above.
 */
const CLOCKED = chart.racePlotOf(RACE, 640, EVALUATING)

/**
 * The race above drawn at 640 pixels, its curves' left edge at 32 and their
 * right edge at 632, the floor at 178 and the top at 32.
 */
const PLOT = chart.racePlotOf(RACE, 640, { ...EVALUATING, episodes: 30 })

enableAutoUnmount(afterEach)

describe('racePlotOf', () => {
  it('draws a gridline every ten episodes, each labeled at the curves’ left edge', () => {
    expect([PLOT.grid, PLOT.counts.map(label => [label.text, label.x, label.y])]).toStrictEqual([
      'M32,178H632M32,129.3H632M32,80.7H632M32,32H632',
      [['0', 22, 182], ['10', 22, 133.3], ['20', 22, 84.7], ['30', 22, 36]]
    ])
  })

  it.each([
    [640, ['1', '10', '100', '1,000', '10,240, the limit']],
    [400, ['1', '10', '100', '10,240, the limit']]
  ])('labels each power of ten and the limit at %i pixels, leaving out one near it', (width, texts) => {
    const steps   = chart.racePlotOf(RACE, width, EVALUATING).steps
    const anchors = ['start', ...texts.slice(2).map(() => 'middle'), 'end']

    expect(steps.map(label => label.text)).toStrictEqual(texts)
    expect(steps.map(label => label.anchor)).toStrictEqual(anchors)
  })

  it('sets each step along a log scale from the curves’ left edge to their right', () => {
    expect(PLOT.steps.map(label => label.x)).toStrictEqual([32, 181.6, 331.2, 480.8, 632])
  })

  it('raises each curve an episode at the step it reached the starter, and runs it on to the limit', () => {
    expect(CLOCKED.curves).toStrictEqual({
      agent  : 'M32,178H181.6V129.3H331.2V80.7H632',
      random : 'M32,178H632'
    })
  })

  it('marks the clock at each stop, its chip kept inside the chart and each dot on its curve', () => {
    expect(CLOCKED.stops.map(mark => [mark.now, mark.x, mark.chip, mark.dots.agent])).toStrictEqual([
      [1, 32, 24, 178], [10, 181.6, 129.6, 129.3], [101, 331.9, 279.9, 80.7], [1018, 482, 430, 80.7],
      [10240, 632, 536, 80.7]
    ])
  })

  it('sets the title beneath the steps at the curves’ left edge', () => {
    expect(PLOT.title).toStrictEqual({ anchor: 'start', text: 'Steps, on a log scale', x: 32, y: 220 })
  })
})

describe('useRace', () => {
  it('draws the race at its box’s width, no narrower than the least the chart takes', async () => {
    const box     = ref<HTMLElement>()
    const plotted = ref<chart.RacePlot>()
    mount(defineComponent({
      setup: () => {
        const plot = chart.useRace(box, RACE)
        return () => {
          plotted.value = plot.value
          return h('div', { ref: box })
        }
      }
    }))
    await nextTick()

    expect(plotted.value?.width).toBe(688)
  })
})
