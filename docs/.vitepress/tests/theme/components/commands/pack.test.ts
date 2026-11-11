// @vitest-environment happy-dom
import { enableAutoUnmount, mount }                        from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick }                                        from 'vue'

import * as pack    from '../../../../lib/commands/pack.ts'
import * as browser from '../../../common/browser.ts'

const { CommandsPack } = await import('../../../../theme/components/commands/pack.tsx')

enableAutoUnmount(afterEach)

beforeEach(() => {
  vi.useFakeTimers()
  return () => vi.useRealTimers()
})

describe('CommandsPack', () => {
  it('writes the demonstration’s tar first as it shows, filling its digest in the manifest', async () => {
    const wrapper = await browser.shown(CommandsPack)

    expect([wrapper.get('[role="status"]').text(), wrapper.get('pre').text()]).toStrictEqual([
      `Wrote dist/runs/${pack.ORDER[0]!.asset}`, expect.stringContaining(pack.ORDER[0]!.sha256)
    ])
  })

  it('shows the window of lines alone, dotting each digest until its tar is written', () => {
    browser.stubSight()
    const wrapper = mount(CommandsPack, { attachTo: document.body })
    const lines   = wrapper.findAll('pre code > span')

    expect([lines.length, wrapper.get('pre').text()]).toStrictEqual([pack.WINDOW, expect.stringContaining('·'.repeat(64))])
  })

  it('rests on the written manifest, then packs again from the first tar', async () => {
    const wrapper = await browser.shown(CommandsPack)

    vi.advanceTimersByTime(260 * (pack.ORDER.length + 1) + 3200)
    await nextTick()

    expect(wrapper.get('[role="status"]').text()).toBe(`Wrote dist/runs/${pack.ORDER[0]!.asset}`)
  })

  it('rings the manifest once every tar is written, where the reader asks for reduced motion', async () => {
    browser.preference.value = 'reduce'
    const wrapper            = await browser.shown(CommandsPack)

    expect([wrapper.get('pre').classes('border-forest-mark'), wrapper.text()]).toStrictEqual([
      true, expect.stringContaining(`${pack.ORDER.length} of ${pack.ORDER.length} tars written`)
    ])
  })
})
