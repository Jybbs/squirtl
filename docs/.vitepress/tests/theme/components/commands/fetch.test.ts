// @vitest-environment happy-dom
import { enableAutoUnmount }                               from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick }                                        from 'vue'

import * as fetch   from '../../../../lib/commands/fetch.ts'
import { timeOf }   from '../../../../lib/commands/release.ts'
import * as browser from '../../../common/browser.ts'

const { CommandsFetch } = await import('../../../../theme/components/commands/fetch.tsx')

enableAutoUnmount(afterEach)

beforeEach(() => {
  vi.useFakeTimers()
  return () => vi.useRealTimers()
})

describe('CommandsFetch', () => {
  it('plays the fetch on its own once it shows, downloading the first tar', async () => {
    const wrapper = await browser.shown(CommandsFetch)

    vi.advanceTimersByTime(40 * 3)
    await nextTick()

    expect(wrapper.get('[role="status"]').text()).toBe(`Downloading ${fetch.MATCHED[0]!.asset}`)
  })

  it('offers the release as packed and one with an altered tar as a group of radios, the first checked', async () => {
    const wrapper = await browser.shown(CommandsFetch)
    const radios  = wrapper.findAll('[role="radio"]')

    expect([
      wrapper.get('[role="radiogroup"]').attributes('aria-label'),
      radios.map(radio => [radio.text(), radio.attributes('aria-checked')])
    ]).toStrictEqual([
      'The release',
      [['The release as packed', 'true'], [`The tar of ${timeOf(fetch.ALTERED.name)} altered`, 'false']]
    ])
  })

  it('fetches the altered release from its start, exiting on the differing digest', async () => {
    browser.preference.value = 'reduce'
    const wrapper            = await browser.shown(CommandsFetch)

    await wrapper.findAll('[role="radio"]')[1]!.trigger('click')
    await nextTick()

    expect([wrapper.get('[role="status"]').text(), wrapper.findAll('li.line-through').length]).toStrictEqual([
      fetch.LONGEST, 2
    ])
  })
})
