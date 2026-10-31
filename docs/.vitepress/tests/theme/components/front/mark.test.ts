// @vitest-environment happy-dom
import { enableAutoUnmount, flushPromises, mount }           from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { defineComponent, h, nextTick, shallowRef }          from 'vue'

import { flightPlanOf, stageKey } from '../../../../lib/front/hero.ts'
import { IDENTITY }               from '../../../../lib/identity/identity.ts'
import { markOf }                 from '../../../../lib/marks/logo.ts'
import { preference, stubSight }  from '../../../common/browser.ts'

const { HeroMark } = await import('../../../../theme/components/front/mark.tsx')

/**
 * How long the whole flight runs, in milliseconds.
 */
const DONE = flightPlanOf(markOf(IDENTITY.name).dots.filter(dot => dot.kind === 'trail').length).done

/**
 * Mounts the mark inside the hero's container beside a copy holding the typeset
 * name and two lines, unless `copied` is unset, with the browser's animations
 * recorded, and returns the mark, the sight that shows it, and the animations
 * started.
 */
async function staged(copied = true) {
  const cancel   = vi.fn<() => void>()
  const played   = vi.spyOn(Element.prototype, 'animate').mockImplementation(() => ({ cancel }) as never)
  const sight    = stubSight()
  const copy     = document.createElement('div')
  copy.innerHTML = '<span data-start></span><span data-glyph>S</span>'
                 + '<span data-rise>One</span><span data-rise>Two</span>'
  const Hero = defineComponent({
    setup: () => () => h('div', { class: 'VPHero' }, [
      h('div', { class: 'container' }, [h(HeroMark), h('div', { class: 'actions' })])
    ])
  })
  const stage   = { copy: shallowRef(copied ? copy : undefined) }
  const provide = { [stageKey as symbol]: stage }
  const wrapper = mount(Hero, { attachTo: document.body, global: { provide } })
  await nextTick()
  return { cancel, played, sight, wrapper }
}

beforeEach(() => {
  vi.useFakeTimers()
  Object.defineProperty(document, 'fonts', { configurable: true, value: { ready: Promise.resolve() } })
})

enableAutoUnmount(afterEach)

describe('HeroMark', () => {
  test('draws the R and the L with Blue walking in each, under a label naming them', async () => {
    const { wrapper } = await staged()
    const mark        = wrapper.find('[role="img"]')

    expect(mark.attributes('aria-label')).toBe('The R and the L of the SquiRtL logo')
    expect(mark.findAll('[data-walk]').map(group => group.attributes('data-walk'))).toStrictEqual(['R', 'L'])
    expect(mark.find('svg').attributes('data-standing')).toBeUndefined()
  })

  test('flies the whole name over the hero as it comes into view, then lands and cancels it', async () => {
    const { cancel, played, sight, wrapper } = await staged()

    sight.show(true)
    await flushPromises()
    const overlay = wrapper.find('[aria-hidden="true"].absolute')
    const hidden  = wrapper.find('[role="img"]').classes('opacity-0')
    const flying  = [overlay.classes('flex'), hidden, played.mock.calls.length > 0]
    vi.advanceTimersByTime(DONE)
    await nextTick()

    expect(flying).toStrictEqual([true, true, true])
    expect(overlay.classes('hidden')).toBe(true)
    expect(cancel).toHaveBeenCalledTimes(played.mock.calls.length)
  })
})

describe('HeroMark in flight', () => {
  test('raises the copy’s lines and the hero’s actions in, each after the one before', async () => {
    const { played, sight } = await staged()

    sight.show(true)
    await flushPromises()
    const risen = played.mock.contexts.filter(each => (each as Element).matches('[data-rise], .actions'))

    expect(risen.map(element => (element as Element).textContent)).toStrictEqual(['One', 'Two', ''])
  })

  test('lands at once where the mark leaves the view mid-flight', async () => {
    const { cancel, played, sight, wrapper } = await staged()

    sight.show(true)
    await flushPromises()
    sight.show(false)
    await nextTick()

    expect(wrapper.find('[aria-hidden="true"].absolute').classes('hidden')).toBe(true)
    expect(cancel).toHaveBeenCalledTimes(played.mock.calls.length)
  })
})

describe('HeroMark at rest', () => {
  test('draws no overlay outside the hero, where the name has no room to fly', () => {
    stubSight()

    expect(mount(HeroMark, { attachTo: document.body }).find('.absolute').exists()).toBe(false)
  })

  test('flies nothing before the name’s copy has mounted', async () => {
    const { played, sight } = await staged(false)

    sight.show(true)
    await flushPromises()

    expect(played).not.toHaveBeenCalled()
  })

  test('stays still and flies nothing where the reader asks for reduced motion', async () => {
    preference.value        = 'reduce'
    const { played, sight } = await staged()

    sight.show(true)
    await flushPromises()
    vi.advanceTimersByTime(1000)

    expect(played).not.toHaveBeenCalled()
  })

  test('walks Blue in place a frame at a time once the mark shows', async () => {
    const { sight, wrapper } = await staged()

    const standing = async () => {
      await nextTick()
      return wrapper.find('[role="img"] svg').attributes('data-standing')
    }

    sight.show(true)
    const first = await standing()
    vi.advanceTimersByTime(420)

    expect([first, await standing()]).toStrictEqual(['', undefined])
  })
})
