// @vitest-environment happy-dom
import { enableAutoUnmount }                   from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { nextTick }                            from 'vue'

import * as order   from '../../../../lib/identity/order.ts'
import * as browser from '../../../common/browser.ts'

const { IdentityOrder } = await import('../../../../theme/components/identity/order.tsx')

enableAutoUnmount(afterEach)

/**
 * Reads how far the plate has drawn each line, as its dash's offset reads it.
 */
const offsets = (wrapper: Awaited<ReturnType<typeof browser.shown>>): (string | undefined)[] =>
  wrapper.findAll('svg[role="img"] path[pathLength]').map(path => path.attributes('stroke-dashoffset'))

describe('IdentityOrder', () => {
  it('draws a line and a switch for each series hue, every line whole under reduced motion', async () => {
    browser.preference.value = 'reduce'
    const wrapper            = await browser.shown(IdentityOrder)

    expect([offsets(wrapper), wrapper.findAll('.identity-switch').map(each => each.attributes('aria-label'))]).toStrictEqual([
      order.RUNS.map(() => '0'),
      order.RUNS.map(run => `${order.tagOf(run)}, ${order.ROLE_WORDS[run.role].toLowerCase()}`)
    ])
    expect(wrapper.text()).toBePublishedProse()
  })

  it('hides a line a reader switches off and draws every other again whole', async () => {
    browser.preference.value = 'reduce'
    const wrapper            = await browser.shown(IdentityOrder)

    await wrapper.findAll('.identity-switch')[0]!.trigger('click')
    await nextTick()
    const hidden = wrapper.get('svg[role="img"] path[pathLength]').attributes('visibility')
    await wrapper.get('.identity-again').trigger('click')
    await nextTick()

    expect([hidden, offsets(wrapper).slice(1)]).toStrictEqual(['hidden', order.RUNS.slice(1).map(() => '0')])
  })

})

describe('IdentityOrder’s pen', () => {
  it('draws the first line on with the nib at its end once the plate shows', async () => {
    vi.useFakeTimers({ toFake: ['performance', 'requestAnimationFrame', 'cancelAnimationFrame'] })
    const wrapper = await browser.shown(IdentityOrder)

    vi.advanceTimersByTime(order.TEMPO.draw / 2)
    await nextTick()
    const [first, second] = offsets(wrapper).map(Number)

    expect([second, wrapper.findAll('.identity-nib').length]).toStrictEqual([1, 1])
    expect(first).toBeGreaterThan(0)
    expect(first).toBeLessThan(1)
    vi.useRealTimers()
  })

  it('rewinds every line drawn before it draws them again', async () => {
    browser.preference.value = 'reduce'
    const wrapper            = await browser.shown(IdentityOrder)
    vi.useFakeTimers({ toFake: ['performance', 'requestAnimationFrame', 'cancelAnimationFrame'] })
    browser.preference.value = 'no-preference'
    await nextTick()

    await wrapper.get('.identity-again').trigger('click')
    vi.advanceTimersByTime(order.TEMPO.rewind / 2)
    await nextTick()

    expect(offsets(wrapper).map(Number).at(-1)).toBeGreaterThan(0)
    vi.useRealTimers()
  })
})
