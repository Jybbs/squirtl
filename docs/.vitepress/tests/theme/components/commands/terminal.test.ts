// @vitest-environment happy-dom
import { enableAutoUnmount }                               from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick }                                        from 'vue'

import * as browser from '../../../common/browser.ts'

const { CommandsTerminal } = await import('../../../../theme/components/commands/terminal.tsx')

enableAutoUnmount(afterEach)

beforeEach(() => {
  vi.useFakeTimers()
  return () => vi.useRealTimers()
})

describe('CommandsTerminal', () => {
  it('plays the run on its own once it shows, listing what each file holds', async () => {
    const wrapper = await browser.shown(CommandsTerminal)

    vi.advanceTimersByTime(120 * 3)
    await nextTick()

    expect([wrapper.get('[role="status"]').text(), wrapper.get('button').text()]).toStrictEqual([
      'Step 80,000 of 2,500,000, episode 8', '$squirtl stop'
    ])
  })

  it('runs squirtl stop as the prompt is pressed, hiding it until the run ends, then trains again', async () => {
    const wrapper = await browser.shown(CommandsTerminal)

    await wrapper.get('button').trigger('click')
    expect([wrapper.get('button').attributes('hidden'), wrapper.text()]).toContain('')
    expect(wrapper.text()).toContain('Wrote the stop file ending the run in data/runs/')

    vi.advanceTimersByTime(900)
    await nextTick()
    expect(wrapper.get('button').attributes('aria-label')).toBe('Run squirtl train')

    await wrapper.get('button').trigger('click')
    expect(wrapper.get('[role="status"]').text()).toBe('Step 0 of 2,500,000, episode 1')
  })

  it('shows the run’s end at once where the reader asks for reduced motion', async () => {
    browser.preference.value = 'reduce'
    const wrapper = await browser.shown(CommandsTerminal)

    expect(wrapper.get('[role="status"]').text()).toMatch(/^Ended at step 2,500,000/u)
  })
})
