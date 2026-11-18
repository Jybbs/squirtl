// @vitest-environment happy-dom
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi }     from 'vitest'

import * as search            from '../../../../lib/methods/search.ts'
import { REST }               from '../../../../lib/widgets/autoplay.ts'
import { KEY, carries }       from '../../../../lib/methods/search/key.ts'
import * as moments           from '../../../../lib/methods/search/moments.ts'
import * as browser           from '../../../common/browser.ts'
import { Recorder, drawInto } from '../../../common/canvas.ts'
import { stopped }            from '../../../common/clock.ts'
import * as pointer           from '../../../common/pointer.ts'

const { MethodsSearch } = await import('../../../../theme/components/methods/search.tsx')

enableAutoUnmount(afterEach)

type Wrapper = ReturnType<typeof mount>

/**
 * Moves the stopped clock `ms` milliseconds on and reads each copy's state.
 */
async function after(wrapper: Wrapper, ms: number): Promise<string[]> {
  vi.advanceTimersByTime(ms)
  await wrapper.vm.$nextTick()
  return states(wrapper)
}

/**
 * Reads whether each copy is dimmed.
 */
function dimmed(wrapper: Wrapper): boolean[] {
  return wrapper.findAll('.search-copy').map(copy => copy.classes().includes('opacity-45'))
}

/**
 * Reads the text of each chip over the copies.
 */
function figures(wrapper: Wrapper): string[] {
  return wrapper.findAll('.sm\\:grid-cols-2 > span').map(chip => chip.text())
}

/**
 * Mounts the widget and shows it on screen, so its playback starts on the
 * case's stopped clock.
 */
function playing(): Promise<Wrapper> {
  drawInto(null)
  return browser.shown(MethodsSearch)
}

/**
 * Reads the state each copy shows, in order.
 */
function states(wrapper: Wrapper): string[] {
  return wrapper.findAll('.search-copy').map(copy => copy.attributes('data-state')!)
}

/**
 * Moves the slider to `key` through its thumb.
 */
async function step(wrapper: Wrapper, key: string): Promise<void> {
  const thumb = wrapper.get('[role="slider"]')
  await thumb.trigger('focusin')
  await thumb.trigger('keydown', { key })
  await wrapper.vm.$nextTick()
}

describe('MethodsSearch', () => {
  it('opens on the demonstration and the search’s figures, the copy that chose a starter ringed', () => {
    drawInto(null)
    const wrapper         = mount(MethodsSearch)
    const last            = search.SEARCH.iterations.at(-1)!
    const { group, slot } = search.SEARCH.found

    expect(states(wrapper).indexOf('win')).toBe(group * search.SIZES.particles + slot)
    expect(figures(wrapper)).toStrictEqual([
      `Demonstration${search.SEARCH.demonstration.length} presses`,
      `Nodes${last.nodes}`,
      `Saved states${last.saved}`,
      `Presses spent${last.spent.toLocaleString('en-US')}`
    ])
    expect(pointer.sliderState(wrapper)).toStrictEqual([String(search.LAST), moments.describe(search.LAST)])
    expect(wrapper.text()).toBePublishedProse()
  })

  it('crosses out each dead copy and rings each winner at the iteration the keys reach', async () => {
    drawInto(null)
    const wrapper = mount(MethodsSearch, { attachTo: document.body })

    await step(wrapper, 'Home')

    expect(states(wrapper)).toStrictEqual(moments.shownOf(0, moments.ENDED).flat().map(each => each.state))
    expect(wrapper.findAll('.search-copy[data-state="dead"] .absolute.inset-0'))
      .toHaveLength(states(wrapper).filter(state => state === 'dead').length)
  })

  it('draws every copy’s screen once the rooms load', async () => {
    vi.spyOn(HTMLImageElement.prototype, 'naturalWidth', 'get').mockReturnValue(2)
    vi.spyOn(HTMLImageElement.prototype, 'naturalHeight', 'get').mockReturnValue(2)
    const recorder = drawInto(new Recorder())
    mount(MethodsSearch)
    await flushPromises()

    expect(recorder.images.length).toBeGreaterThanOrEqual(search.SIZES.groups * search.SIZES.particles)
  })
})

describe('MethodsSearch’s copies', () => {
  it('dims the copy holding the starter’s badge once a reader presses the milestone entry', async () => {
    drawInto(null)
    const wrapper         = mount(MethodsSearch, { attachTo: document.body })
    const { group, slot } = search.SEARCH.found
    const entry           = KEY.findIndex(({ role }) => role === 'milestone')

    await wrapper.findAll('button[aria-pressed]')[entry]!.trigger('click')

    expect(dimmed(wrapper)[group * search.SIZES.particles + slot]).toBe(true)
  })
})

describe('MethodsSearch’s slider', () => {
  it('moves nothing under a pointer pressing and sweeping across the copies', async () => {
    drawInto(null)
    const wrapper = mount(MethodsSearch, { attachTo: document.body })
    const copies  = pointer.laidOut(wrapper.get('ol'), 600)
    const before  = pointer.sliderState(wrapper)

    await pointer.press(copies, 60)
    await pointer.sweep(copies, [120, 300, 540])

    expect(pointer.sliderState(wrapper)).toStrictEqual(before)
  })
})

describe('MethodsSearch’s key', () => {
  it.each(KEY.map((entry, n) => ({ n, name: entry.name })))(
    'dims every copy without the mark of $name once a reader presses it',
    async ({ n }) => {
      drawInto(null)
      const wrapper = mount(MethodsSearch, { attachTo: document.body })
      await step(wrapper, 'Home')
      const marked = moments.shownOf(0, moments.ENDED).flat().map(each => carries(each, n))

      await wrapper.findAll('button[aria-pressed]')[n]!.trigger('click')

      expect(dimmed(wrapper).map(dim => !dim)).toStrictEqual(marked)
    }
  )

  it('lifts the dimming once a reader presses the same entry again', async () => {
    drawInto(null)
    const wrapper = mount(MethodsSearch, { attachTo: document.body })
    await step(wrapper, 'Home')
    const entry = wrapper.findAll('button[aria-pressed]')[1]!

    await entry.trigger('click')
    await entry.trigger('click')

    expect(dimmed(wrapper)).toStrictEqual(dimmed(wrapper).map(() => false))
  })

  it('dims by the entry a mouse rests on, and lifts the dimming once it leaves', async () => {
    drawInto(null)
    const wrapper = mount(MethodsSearch, { attachTo: document.body })
    await step(wrapper, 'Home')
    const entry = wrapper.findAll('button[aria-pressed]')[1]!

    await entry.trigger('pointerenter', { pointerType: 'mouse' })
    const resting = dimmed(wrapper)
    await entry.trigger('pointerleave')

    expect([resting, dimmed(wrapper)]).toStrictEqual([
      moments.shownOf(0, moments.ENDED).flat().map(each => !carries(each, 1)), resting.map(() => false)
    ])
  })
})

describe('MethodsSearch’s playback', () => {
  stopped('plays the first iteration press by press once shown, then moves copies to their winners', async () => {
    const wrapper = await playing()

    const pressing = await after(wrapper, moments.TIMING.press * 2)
    const moved    = await after(wrapper, moments.ROLLING + moments.TIMING.move)

    expect([pointer.sliderState(wrapper)[0], pressing, moved]).toStrictEqual([
      '0', pressing.map(() => ''), moments.shownOf(0, moments.MOVED).flat().map(each => each.state)
    ])
  })

  stopped('goes on to the next iteration, every copy pressing on from its winner’s node', async () => {
    const wrapper = await playing()
    const moved   = moments.ROLLING + moments.TIMING.move

    await after(wrapper, moved)
    const pressing = await after(wrapper, moments.ITERATION - moved + moments.TIMING.press / 2)

    expect([pointer.sliderState(wrapper)[0], pressing]).toStrictEqual(['1', pressing.map(() => '')])
  })

  stopped('rests on the demonstration after the last iteration, then starts again from the first', async () => {
    const wrapper = await playing()

    await after(wrapper, search.LAST * moments.ITERATION)
    const resting = pointer.sliderState(wrapper)[0]
    await after(wrapper, REST)

    expect([resting, pointer.sliderState(wrapper)[0]]).toStrictEqual([String(search.LAST), '0'])
  })

  stopped('stands on the demonstration under reduced motion', async () => {
    const wrapper = await playing()

    await after(wrapper, moments.TIMING.press)
    browser.preference.value = 'reduce'
    await wrapper.vm.$nextTick()

    expect(pointer.sliderState(wrapper)[0]).toBe(String(search.LAST))
  })
})
