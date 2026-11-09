// @vitest-environment happy-dom
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi }    from 'vitest'
import { nextTick }                               from 'vue'

import * as experience        from '../../../../lib/methods/experience.ts'
import { count }              from '../../../../lib/widgets/numbers.ts'
import * as browser           from '../../../common/browser.ts'
import { Recorder, drawInto } from '../../../common/canvas.ts'
import * as pointer           from '../../../common/pointer.ts'

const { MethodsExperience } = await import('../../../../theme/components/methods/experience.tsx')

enableAutoUnmount(afterEach)

/**
 * Reads the values the chips show, the median age, the newest read, and the
 * oldest.
 */
const chips = (wrapper: ReturnType<typeof mount>): string[] =>
  wrapper.findAllComponents({ name: 'Chip' }).map(chip => chip.text())

/**
 * Reads the chips update `k` shows.
 */
function chipsOf(k: number): string[] {
  const { median, newest, oldest } = experience.figuresOf(experience.agesOf(k))
  return [`Median agesteps${count(median)}`, `Newest readsteps${count(newest)}`, `Oldest readsteps${count(oldest)}`]
}

describe('MethodsExperience', () => {
  it('opens on the first update, an arc to each step it reads and a window under every fourth', () => {
    drawInto(null)
    const wrapper = mount(MethodsExperience)

    expect([
      pointer.sliderState(wrapper),
      chips(wrapper),
      wrapper.findAll('path').length,
      wrapper.findAll('.experience-window').length,
      wrapper.findAll('.experience-tick').map(tick => tick.text())
    ]).toStrictEqual([
      ['0', 'Update 1'],
      chipsOf(0),
      experience.MEMORY.batch + 1,
      experience.MEMORY.batch / experience.EVERY,
      ['100,000 ago', '75,000 ago', '50,000 ago', '25,000 ago', 'now']
    ])
    expect(wrapper.text()).toBePublishedProse()
  })

  it('draws each window once the rooms load', async () => {
    const recorder = drawInto(new Recorder())
    mount(MethodsExperience)
    await flushPromises()

    expect(recorder.images.length).toBeGreaterThanOrEqual(experience.MEMORY.batch / experience.EVERY)
  })
})

describe('MethodsExperience’s playback', () => {
  it('moves to the next update on the arrow key, the arcs settling on its reads', async () => {
    drawInto(null)
    browser.preference.value = 'reduce'
    const wrapper = mount(MethodsExperience, { attachTo: document.body })
    const thumb   = wrapper.get('[role="slider"]')

    await thumb.trigger('focusin')
    await thumb.trigger('keydown', { key: 'ArrowRight' })
    await flushPromises()

    expect([pointer.sliderState(wrapper), chips(wrapper), wrapper.findAll('path')[0]!.attributes('d')])
      .toStrictEqual([['1', 'Update 2'], chipsOf(1), experience.arcOf(experience.agesOf(1)[0]!)])
    browser.preference.value = 'no-preference'
  })

  it('plays an update a beat once it shows', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'performance', 'requestAnimationFrame', 'cancelAnimationFrame'] })
    drawInto(null)
    const sight   = browser.stubSight()
    const wrapper = mount(MethodsExperience, { attachTo: document.body })
    await nextTick()

    sight.show(true)
    await nextTick()
    const first = chips(wrapper)
    vi.advanceTimersByTime(experience.BEAT)
    await nextTick()

    expect([first, chips(wrapper)]).toStrictEqual([chipsOf(1), chipsOf(2)])
    vi.useRealTimers()
  })
})
