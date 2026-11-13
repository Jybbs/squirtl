// @vitest-environment happy-dom
import { enableAutoUnmount }                               from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick }                                        from 'vue'

import * as seam    from '../../../../lib/identity/seam.ts'
import * as browser from '../../../common/browser.ts'
import * as pointer from '../../../common/pointer.ts'

const { IdentityLogo } = await import('../../../../theme/components/identity/logo.tsx')

enableAutoUnmount(afterEach)

beforeEach(() => {
  vi.useFakeTimers()
  return () => vi.useRealTimers()
})

/**
 * Reads where the seam stands, from the style the widget sets on itself.
 */
const seamOf = (wrapper: Awaited<ReturnType<typeof browser.shown>>): string =>
  (wrapper.element as HTMLElement).style.getPropertyValue('--seam')

/**
 * Reads the entry each ground's key rings.
 */
const ringed = (wrapper: Awaited<ReturnType<typeof browser.shown>>): string[] =>
  wrapper.findAll('.identity-entry[data-on="true"]').map(entry => entry.find('.text-small').text())

describe('IdentityLogo', () => {
  it('draws the logo on both grounds over a key to the trail on each', async () => {
    const wrapper = await browser.shown(IdentityLogo)

    expect([
      wrapper.findAll('.identity-ground-mark').map(ground => ground.attributes('data-scheme')),
      wrapper.findAll('.identity-entry').length
    ]).toStrictEqual([['light', 'dark'], 8])
    expect(wrapper.text()).toBePublishedProse()
  })

})

describe('IdentityLogo’s playback', () => {
  it('holds the seam in the middle a longer beat, then nudges it toward the dark ground', async () => {
    const wrapper = await browser.shown(IdentityLogo)

    vi.advanceTimersByTime(seam.TEMPO.wait - 1)
    await nextTick()
    const held = seamOf(wrapper)
    vi.advanceTimersByTime(1)
    await nextTick()

    expect([held, seamOf(wrapper)]).toStrictEqual(['50%', `${seam.NUDGE[2]}%`])
  })

  it('lights the trail a dot a beat on each ground from the first, the key ringing the oldest third', async () => {
    const wrapper = await browser.shown(IdentityLogo)
    const lit     = () => wrapper.findAll('.identity-dot').filter(dot => dot.attributes('opacity') === '1').length

    const first = lit()
    vi.advanceTimersByTime(seam.TEMPO.fill)
    await nextTick()

    expect([lit() - first, ringed(wrapper)]).toStrictEqual([2, ['The first third, oldest', 'The first third, oldest']])
  })

  it('starts the trail over from its first dot once it has rested after the last', async () => {
    const wrapper = await browser.shown(IdentityLogo)
    const unlit   = () => wrapper.findAll('.identity-dot[opacity="0.12"]').length
    const opening = unlit()

    vi.advanceTimersByTime(seam.FILLED.length * seam.TEMPO.fill)
    await nextTick()
    const whole = unlit()
    vi.advanceTimersToNextTimer()
    await nextTick()

    expect([whole, unlit()]).toStrictEqual([0, opening])
  })

})

describe('IdentityLogo’s stillness and keys', () => {
  it('stands the seam where it settles and the trail whole under reduced motion, the key ringing the dot still ahead', async () => {
    browser.preference.value = 'reduce'
    const wrapper            = await browser.shown(IdentityLogo)

    expect([seamOf(wrapper), wrapper.findAll('.identity-dot[opacity="0.12"]').length, ringed(wrapper)])
      .toStrictEqual(['50%', 0, ['The dot still ahead', 'The dot still ahead']])
  })

  it('moves the seam where the arrow keys take it, reading the share on each ground', async () => {
    browser.preference.value = 'reduce'
    const wrapper            = await browser.shown(IdentityLogo)
    const thumb              = wrapper.findAll('[role="slider"]')[0]!

    await thumb.trigger('focusin')
    await thumb.trigger('keydown', { key: 'ArrowRight' })
    await nextTick()

    expect([seamOf(wrapper), pointer.sliderState(wrapper)]).toStrictEqual(['51%', ['51', seam.seamWords(51)]])
  })
})
