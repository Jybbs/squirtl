// @vitest-environment happy-dom
import { type VueWrapper, enableAutoUnmount, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick }                                        from 'vue'

import * as browser         from '../../../common/browser.ts'
import { ResultsAggregate } from '../../../../theme/components/results/aggregate.tsx'

enableAutoUnmount(afterEach)

/**
 * Reads the buttons over each column.
 */
const columnsOf = (wrapper: VueWrapper) => wrapper.findAll('ul[aria-label="Runs by group"] button')

/**
 * Mounts the widget with its plot 688 pixels wide, every animation an element
 * plays recorded rather than played.
 */
async function mounted(): Promise<VueWrapper> {
  vi.spyOn(Element.prototype, 'animate').mockReturnValue({ cancel: () => {} } as unknown as Animation)
  const resize  = browser.stubSize()
  const wrapper = mount(ResultsAggregate, { attachTo: document.body })
  await nextTick()
  resize(688, 240)
  await nextTick()
  return wrapper
}

/**
 * Reads each run's group in the drawing, the one a press switches its seed
 * from.
 */
const runGroupsOf = (wrapper: VueWrapper) =>
  wrapper.findAll('svg g').filter(group => group.attributes('style')?.includes('transition-delay'))

/**
 * Reads every switch of a seed.
 */
const switchesOf = (wrapper: VueWrapper) => wrapper.findAll('ul[aria-label="Seeds kept"] button')

/**
 * Rests a mouse on the plot `clientX` pixels from its left edge until its
 * column opens.
 */
async function rested(wrapper: VueWrapper, clientX: number): Promise<void> {
  const plot = wrapper.get('.h-race-plot')
  vi.spyOn(plot.element, 'getBoundingClientRect').mockReturnValue({ left: 0, width: 688 } as DOMRect)
  await plot.trigger('pointermove', { clientX, pointerType: 'mouse' })
  vi.advanceTimersByTime(300)
  await nextTick()
}

beforeEach(() => {
  browser.preference.value = 'reduce'
})

describe('ResultsAggregate’s columns', () => {
  it('opens a column a reader presses, naming its runs, and shuts it on a second press', async () => {
    const wrapper = await mounted()
    const spoken  = () => wrapper.get('p.visually-hidden').text()
    await columnsOf(wrapper)[1]!.trigger('click')
    const opened = spoken()
    await columnsOf(wrapper)[1]!.trigger('click')
    expect([opened, spoken()])
      .toStrictEqual(['PPO, 5 runs: seed 1 100%; seed 2 100%; seed 3 100%; seed 4 100%; seed 5 100%', ''])
  })

  it('names a run whose seed is left out as such', async () => {
    const wrapper = await mounted()
    await switchesOf(wrapper)[0]!.trigger('click')
    await columnsOf(wrapper)[4]!.trigger('click')
    expect(wrapper.get('p.visually-hidden').text())
      .toBe('PQN along the curriculum, 5 runs: seed 1 0%, left out; '
          + 'seed 2 0%; seed 3 0%; seed 4 0%; seed 5 0%')
  })

  it('fans a pressed column’s runs out by seed, half a beat apart, and hides its ball', async () => {
    const wrapper = await mounted()
    await columnsOf(wrapper)[1]!.trigger('click')
    expect([
      runGroupsOf(wrapper).slice(5, 10).map(run => run.attributes('style')),
      wrapper.findAll('svg g.transition-opacity').map(group => group.classes('opacity-0'))
    ]).toStrictEqual([
      [-40, -20, 0, 20, 40].map((x, n) =>
        `transition-delay: ${n * 75}ms; transition-duration: 600ms; transform: translate(${x}px, 8px);`),
      [false, true, false, false, false]
    ])
  })
})

describe('ResultsAggregate’s columns under a mouse', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  it.each([
    ['a mouse resting on a column', 'mouse', 300, 'pointer-events-auto'],
    ['a mouse passing across', 'mouse', 100, 'opacity-0'],
    ['a touch', 'touch', 300, 'opacity-0']
  ])('opens a column’s runs after %s: %s', async (_, pointerType, rest, shown) => {
    const wrapper = await mounted()
    const plot    = wrapper.get('.h-race-plot')
    vi.spyOn(plot.element, 'getBoundingClientRect').mockReturnValue({ left: 0, width: 688 } as DOMRect)
    await plot.trigger('pointermove', { clientX: 200, pointerType })
    vi.advanceTimersByTime(rest)
    await nextTick()
    expect(runGroupsOf(wrapper)[5]!.classes()).toContain(shown)
  })

  it.each([
    ['just past the scale', 60, 0],
    ['just short of the second column’s edge', 160, 0],
    ['just past it', 175, 5]
  ])('opens the column a mouse rests on %s', async (_, clientX, first) => {
    const wrapper = await mounted()
    await rested(wrapper, clientX)
    expect(runGroupsOf(wrapper)[first]!.classes()).toContain('pointer-events-auto')
  })

  it('opens the column a mouse rests on over the one pressed, and the pressed one once it leaves', async () => {
    const wrapper = await mounted()
    const open    = () => runGroupsOf(wrapper).findIndex(run => run.classes('pointer-events-auto')) / 5
    await columnsOf(wrapper)[3]!.trigger('click')
    await rested(wrapper, 200)
    const over = open()
    await wrapper.get('.h-race-plot').trigger('pointerleave')
    vi.advanceTimersByTime(300)
    await nextTick()
    expect([over, open()]).toStrictEqual([1, 3])
  })

  it('shuts the runs a mouse opened once it leaves the plot', async () => {
    const wrapper = await mounted()
    await rested(wrapper, 200)
    await wrapper.get('.h-race-plot').trigger('pointerleave')
    vi.advanceTimersByTime(300)
    await nextTick()
    expect(runGroupsOf(wrapper)[5]!.classes()).toContain('opacity-0')
  })
})
