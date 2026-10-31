// @vitest-environment happy-dom
import { type VueWrapper, enableAutoUnmount, mount }         from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { nextTick, ref }                                     from 'vue'

import type * as race from '../../../../lib/front/race.ts'
import * as browser   from '../../../common/browser.ts'
import * as pointer   from '../../../common/pointer.ts'

/**
 * A mounted widget beside the sight a case shows it through.
 */
interface Mounted {
  sight   : browser.Sight
  wrapper : VueWrapper
}

const standIn = ref<race.Race | null>(null)

vi.mock('../../../../lib/front/race.ts', async original => {
  const module = await original<typeof import('../../../../lib/front/race.ts')>()
  return { ...module, raceOf: () => standIn.value ?? module.raceOf() }
})

const { StoryRace } = await import('../../../../theme/components/front/race.tsx')

enableAutoUnmount(afterEach)

/**
 * Mounts the widget into the page.
 */
async function mounted(): Promise<Mounted> {
  const sight   = browser.stubSight()
  const wrapper = mount(StoryRace, { attachTo: document.body })
  await nextTick()
  return { sight, wrapper }
}

/**
 * Reads the key's heads and each player's name beside its figures.
 */
const scores = (wrapper: VueWrapper) => wrapper.findAll('.key-figures > span').map(cell => cell.text())

beforeEach(() => {
  browser.preference.value = 'reduce'
  standIn.value            = null
  vi.useFakeTimers()
})

describe('StoryRace under reduced motion', () => {
  test('shows the race at its limit at once, counting the episodes reaching the starter', async () => {
    const { sight, wrapper } = await mounted()

    sight.show(true)
    await nextTick()

    expect(pointer.sliderState(wrapper)).toStrictEqual([
      '120', '10,240 steps: the agent has reached the starter in 30 of 30 episodes and random presses in 8'
    ])
    expect(scores(wrapper)).toStrictEqual([
      '', 'Reached it', 'Steps to it', 'The agent', '30 of 30', '75', 'Random presses', '8 of 30', '6,449'
    ])
    expect(wrapper.text()).toContain('Episodes that have reached the starter')
  })

  test('draws the chart with each player’s curve, its clock’s chip, and a dot on each', async () => {
    const { wrapper } = await mounted()
    const chart       = wrapper.get('svg[viewBox]')

    expect(chart.findAll('path.stroke-agent')).toHaveLength(2)
    expect(chart.findAll('circle').map(dot => dot.classes())).toStrictEqual([
      ['stroke-ground', 'fill-agent'], ['stroke-ground', 'fill-random']
    ])
    expect(chart.findAll('.clock-chip')).toHaveLength(1)
    expect(chart.text()).toContain('Steps, on a log scale')
  })

  test('reads no steps for a player none of whose episodes reached the starter', async () => {
    standIn.value     = { agent: [{ reached: true, steps: 1 }], random: [{ reached: false, steps: 10240 }] }
    const { wrapper } = await mounted()

    expect(scores(wrapper).slice(3))
      .toStrictEqual(['The agent', '1 of 1', '1', 'Random presses', '0 of 1', 'None'])
  })
})

describe('StoryRace playing', () => {
  beforeEach(() => {
    browser.preference.value = 'no-preference'
  })

  test('runs the clock a stop each beat once the widget shows, naming the step on its chip', async () => {
    const { sight, wrapper } = await mounted()

    sight.show(true)
    await nextTick()
    const first = pointer.sliderState(wrapper)[0]
    vi.advanceTimersByTime(50 * 29)
    await nextTick()

    expect([first, pointer.sliderState(wrapper)[0], wrapper.get('.clock-chip + rect + text').text()])
      .toStrictEqual(['1', '30', '10 steps'])
  })

  test('rests at the limit, then runs the clock again from the first step', async () => {
    const { sight, wrapper } = await mounted()

    sight.show(true)
    vi.advanceTimersByTime(50 * 120)
    await nextTick()
    const rested = pointer.sliderState(wrapper)[0]
    vi.advanceTimersByTime(5000)
    await nextTick()

    expect([rested, pointer.sliderState(wrapper)[0]]).toStrictEqual(['120', '1'])
  })
})

describe('StoryRace held by a reader', () => {
  beforeEach(() => {
    browser.preference.value = 'no-preference'
  })

  test('sets the clock by the keys and holds it while the slider has focus until it loses it', async () => {
    const { sight, wrapper } = await mounted()
    const thumb              = wrapper.get('[role="slider"]')

    sight.show(true)
    await thumb.trigger('focusin')
    await thumb.trigger('keydown', { key: 'End' })
    await thumb.trigger('keydown', { key: 'ArrowLeft' })
    vi.advanceTimersByTime(1000)
    await nextTick()
    const held = pointer.sliderState(wrapper)[0]
    await thumb.trigger('focusout')
    vi.advanceTimersByTime(50)
    await nextTick()

    expect([held, pointer.sliderState(wrapper)[0]]).toStrictEqual(['119', '120'])
  })

  test('holds the clock still while a mouse moves across the chart', async () => {
    const { sight, wrapper } = await mounted()
    const control            = pointer.controlOf(wrapper, 120)

    sight.show(true)
    await nextTick()
    const rested = pointer.sliderState(wrapper)[0]
    await pointer.sweep(control, [10, 60, 110])
    vi.advanceTimersByTime(500)
    await nextTick()

    expect(pointer.sliderState(wrapper)[0]).toBe(rested)
  })

  test('sets the clock at the stop a press on the chart lands on', async () => {
    const { wrapper } = await mounted()
    const control     = pointer.controlOf(wrapper, 120)

    await pointer.press(control, 60)

    expect(pointer.sliderState(wrapper)[0]).toBe('60')
  })
})
