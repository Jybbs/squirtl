// @vitest-environment happy-dom
import { type VueWrapper, enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi }          from 'vitest'
import { nextTick }                                                 from 'vue'

import * as watching          from '../../../../lib/commands/watch.ts'
import * as browser           from '../../../common/browser.ts'
import { Recorder, drawInto } from '../../../common/canvas.ts'
import * as pointer           from '../../../common/pointer.ts'

const { CommandsWatch } = await import('../../../../theme/components/commands/watch.tsx')

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'performance', 'requestAnimationFrame', 'cancelAnimationFrame'] })
})

afterEach(() => {
  vi.useRealTimers()
})

enableAutoUnmount(afterEach)

/**
 * Reads each check's chip as it reads.
 */
const checks = (wrapper: VueWrapper): string[] => wrapper.findAll('.watch-status').map(each => each.text())

/**
 * Mounts the widget drawing into `recorder` and lets the rooms load.
 */
async function mounted(recorder: Recorder | null = new Recorder()) {
  drawInto(recorder)
  const sight   = browser.stubSight()
  const wrapper = mount(CommandsWatch, { attachTo: document.body })
  await flushPromises()
  return { sight, wrapper }
}

describe('CommandsWatch', () => {
  it('waits with the window closed until it shows', async () => {
    const { wrapper } = await mounted()

    expect([checks(wrapper), pointer.sliderState(wrapper)]).toStrictEqual([
      ['Digestwaiting', 'Returnwaiting'], ['1', 'Press 1 of 181, Right']
    ])
    expect(wrapper.text()).toBePublishedProse()
  })

  it('checks the digest, plays every press, and checks the return once it shows', async () => {
    const recorder          = new Recorder()
    const { sight, wrapper } = await mounted(recorder)

    sight.show(true)
    vi.advanceTimersByTime(watching.PHASES.digest)
    await nextTick()
    const before = checks(wrapper)
    vi.advanceTimersByTime(watching.PHASES.play + 600 - watching.PHASES.digest)
    await nextTick()

    expect([before, checks(wrapper), pointer.sliderState(wrapper)[0]]).toStrictEqual([
      ['Digestmatches', 'Returnwaiting'], ['Digestmatches', 'Returnmatches'], '181'
    ])
    expect(recorder.images.length).toBeGreaterThan(0)
  })
})

describe('CommandsWatch at a hold', () => {
  it('stands at the hold under reduced motion, and leaves the screen blank without a context', async () => {
    browser.preference.value = 'reduce'
    const { sight, wrapper } = await mounted(null)

    sight.show(true)
    await nextTick()

    expect(checks(wrapper)).toStrictEqual(['Digestmatches', 'Returnmatches'])
  })

  it('holds the playback on the byte a press lands on', async () => {
    const { wrapper } = await mounted()
    const control     = wrapper.get("[data-part='control']")
    vi.spyOn(control.element, 'getBoundingClientRect').mockReturnValue({ height: 50, left: 0, top: 0, width: 130 } as DOMRect)
    vi.spyOn(window, 'getComputedStyle').mockReturnValue({ gridTemplateColumns: Array.from({ length: 13 }, () => '10px').join(' ') } as CSSStyleDeclaration)
    control.element.setPointerCapture = () => {}

    await control.trigger('pointerdown', { clientX: 25, clientY: 1, pointerId: 1, pointerType: 'mouse' })
    await control.trigger('pointermove', { buttons: 1, clientX: 35, clientY: 1, pointerType: 'mouse' })
    await control.trigger('pointermove', { buttons: 0, clientX: 125, clientY: 45, pointerType: 'mouse' })

    expect(pointer.sliderState(wrapper)[0]).toBe('4')
  })
})

describe('CommandsWatch’s slider', () => {
  it('holds on the first press at Home, the reset before it never shown', async () => {
    const { wrapper } = await mounted()
    const thumb       = wrapper.get('[role="slider"]')

    await thumb.trigger('focusin')
    await thumb.trigger('keydown', { key: 'End' })
    await thumb.trigger('keydown', { key: 'Home' })
    await nextTick()

    expect(pointer.sliderState(wrapper)).toStrictEqual(['1', 'Press 1 of 181, Right'])
  })

  it('replays from the reset when the slider moves back once the window shows', async () => {
    const recorder           = new Recorder()
    const { sight, wrapper } = await mounted(recorder)
    const thumb              = wrapper.get('[role="slider"]')

    sight.show(true)
    vi.advanceTimersByTime(watching.PHASES.play)
    await nextTick()
    await thumb.trigger('focusin')
    await thumb.trigger('keydown', { key: 'End' })
    await nextTick()
    const drawn = recorder.images.length
    await thumb.trigger('keydown', { key: 'Home' })
    await nextTick()

    expect([pointer.sliderState(wrapper)[0], recorder.images.length > drawn]).toStrictEqual(['1', true])
  })
})
