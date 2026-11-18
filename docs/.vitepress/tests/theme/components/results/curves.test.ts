// @vitest-environment happy-dom
import { type VueWrapper, enableAutoUnmount, flushPromises, mount }   from '@vue/test-utils'
import { type FakeTimersConfig, afterEach, describe, expect, it, vi } from 'vitest'
import { nextTick }                                                   from 'vue'

import { BEAT }     from '../../../../lib/widgets/motion.ts'
import * as browser from '../../../common/browser.ts'
import { held }     from '../../../common/results.ts'

const { ResultsCurves } = await import('../../../../theme/components/results/curves.tsx')

enableAutoUnmount(afterEach)

/**
 * The clocks a case tracing a curve over time fakes, `Date` among the timers
 * since `useTransition` times each frame through `Date.now`.
 */
const FAKED: FakeTimersConfig = {
  toFake: ['Date', 'setTimeout', 'clearTimeout', 'requestAnimationFrame', 'cancelAnimationFrame']
}

/**
 * Reads each toggle's name and whether it is pressed.
 */
const toggles = (wrapper: VueWrapper) =>
  wrapper.findAll('button').map(button => [button.find('span:nth-child(2)').text(), button.attributes('aria-pressed')])

/**
 * Reads how far each group's curve has traced out, as the width its clip
 * opens across.
 */
const traces = (wrapper: VueWrapper) => wrapper.findAll('clipPath rect').map(rect => Number(rect.attributes('width')))

describe('ResultsCurves', () => {
  it('draws nothing until a run is committed', () => {
    held.runs = false
    expect(mount(ResultsCurves).html()).toBe('')
  })

  it('presses the groups of the agent parting furthest, and toggles a group on a press', async () => {
    held.runs     = true
    const wrapper = mount(ResultsCurves)

    expect(toggles(wrapper)).toStrictEqual([
      ['Deep Q-network', 'false'], ['PPO', 'false'], ['PPO, curriculum', 'false'], ['PQN', 'true'],
      ['PQN, curriculum', 'true']
    ])

    await wrapper.findAll('button')[1]!.trigger('click')
    await wrapper.findAll('button')[3]!.trigger('click')

    expect(toggles(wrapper).map(([, pressed]) => pressed))
      .toStrictEqual(['false', 'true', 'false', 'false', 'true'])
    expect(wrapper.text()).toBePublishedProse()
  })

  it('moves focus along the toggles on the arrow keys, to either end on Home and End, and wraps past the last', async () => {
    held.runs     = true
    const wrapper = mount(ResultsCurves, { attachTo: document.body })
    const buttons = wrapper.findAll<HTMLButtonElement>('button')
    const focused = () => buttons.findIndex(button => button.element === document.activeElement)
    const press   = async (key: string) => {
      await wrapper.find<HTMLButtonElement>('button:focus').trigger('keydown', { key })
      await flushPromises()
      return focused()
    }

    buttons[0]!.element.focus()
    await buttons[0]!.trigger('focus')

    expect([await press('ArrowRight'), await press('ArrowRight'), await press('End'), await press('ArrowRight'), await press('ArrowLeft'), await press('Home')])
      .toStrictEqual([1, 2, 4, 0, 4, 0])
  })

})

describe('ResultsCurves’s traces', () => {
  it('stands every pressed curve whole at once under reduced motion, and none released', async () => {
    held.runs                = true
    browser.preference.value = 'reduce'
    const wrapper            = mount(ResultsCurves)

    await nextTick()

    expect(traces(wrapper).map(width => width > 100)).toStrictEqual([false, false, false, true, true])
  })

  it('traces a curve pressed under reduced motion out whole at once', async () => {
    held.runs                = true
    browser.preference.value = 'reduce'
    const wrapper            = mount(ResultsCurves)

    await nextTick()
    await wrapper.findAll('button')[1]!.trigger('click')
    await nextTick()

    expect(traces(wrapper).map(width => width > 100)).toStrictEqual([false, true, false, true, true])
  })

  it('holds every curve back until the plot first comes into view', async () => {
    held.runs = true
    vi.useFakeTimers(FAKED)
    const sight   = browser.stubSight()
    const wrapper = mount(ResultsCurves, { attachTo: document.body })

    await vi.advanceTimersByTimeAsync(2000)
    const before = traces(wrapper)
    sight.show(true)
    await vi.advanceTimersByTimeAsync(2000)

    expect([before.map(width => width > 100), traces(wrapper).map(width => width > 100)]).toStrictEqual([
      [false, false, false, false, false], [false, false, false, true, true]
    ])
  })

})

describe('ResultsCurves’s releases', () => {
  it('draws a released curve back and traces a newly pressed one out at once, waiting on no earlier press', async () => {
    held.runs = true
    vi.useFakeTimers(FAKED)
    const sight   = browser.stubSight()
    const wrapper = mount(ResultsCurves, { attachTo: document.body })

    await vi.advanceTimersByTimeAsync(0)
    sight.show(true)
    // The opening traces take four beats, the later one a beat behind.
    await vi.advanceTimersByTimeAsync(5 * BEAT)
    await wrapper.findAll('button')[3]!.trigger('click')
    await wrapper.findAll('button')[0]!.trigger('click')
    await vi.advanceTimersByTimeAsync(700)

    expect(traces(wrapper).map(width => width > 100)).toStrictEqual([true, false, false, false, true])
  })
})

describe('ResultsCurves’s figures', () => {
  it('lists each group’s figures in a fixed slot under the plot, random presses last', () => {
    held.runs     = true
    const wrapper = mount(ResultsCurves)

    expect(wrapper.text()).toMatch(/Random pressesReached it0\.10 \[0\.00, 0\.25\] over 7$/u)
  })
})

