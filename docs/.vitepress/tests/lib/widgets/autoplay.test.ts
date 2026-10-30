// @vitest-environment happy-dom
import { enableAutoUnmount, mount }                          from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { defineComponent, h, nextTick, ref }                 from 'vue'

import { type Autoplay, type Ticking, useAutoplay } from '../../../lib/widgets/autoplay.ts'
import * as browser                                 from '../../common/browser.ts'

/**
 * Mounts a widget playing a run of `length` beats, recording each call the
 * autoplay makes, and returns its log, its autoplay, and the sight a case shows
 * it through.
 */
async function played(
  length : number,
  rest   : boolean = false
): Promise<{ autoplay: Autoplay, log: string[], sight: browser.Sight, unmount: () => void }> {
  const sight         = browser.stubSight()
  const log: string[] = []
  let at              = 0
  let autoplay!: Autoplay
  const ticking: Ticking = {
    beat   : 100,
    done   : () => at >= length,
    finish : () => { log.push('finish') },
    tick   : () => {
      at++
      log.push(`tick ${at}`)
    },
    ...rest ? {
      rest    : 500,
      restart : () => {
        at = 0
        log.push('restart')
      }
    } : {}
  }
  const wrapper = mount(defineComponent({
    setup: () => {
      const node = ref<HTMLElement>()
      autoplay = useAutoplay(node, ticking)
      return () => h('div', { ref: node })
    }
  }))
  await nextTick()
  return { autoplay, log, sight, unmount: () => wrapper.unmount() }
}

beforeEach(() => {
  vi.useFakeTimers()
})

enableAutoUnmount(afterEach)

describe('useAutoplay', () => {
  test('plays a beat at a time once the widget shows, and stops at the end of a run', async () => {
    const { log, sight } = await played(2)

    sight.show(true)
    vi.advanceTimersByTime(1000)

    expect(log).toStrictEqual(['tick 1', 'tick 2'])
  })

  test('holds no beat while the widget stays off screen', async () => {
    const { log, sight } = await played(2)

    sight.show(false)
    vi.advanceTimersByTime(1000)

    expect(log).toStrictEqual([])
  })

  test('rests on the end of a run that repeats, then starts it again', async () => {
    const { log, sight } = await played(1, true)

    sight.show(true)
    vi.advanceTimersByTime(650)

    expect(log).toStrictEqual(['tick 1', 'restart', 'tick 1'])
  })
})

describe('useAutoplay holding and ending', () => {
  test('holds while a reason stands and plays on once none does', async () => {
    const { autoplay, log, sight } = await played(3)

    sight.show(true)
    autoplay.hold('pointer', true)
    autoplay.hold('keys', true)
    autoplay.hold('pointer', false)
    vi.advanceTimersByTime(1000)
    const held = [...log]
    autoplay.hold('keys', false)
    vi.advanceTimersByTime(1000)

    expect([held, log]).toStrictEqual([['tick 1'], ['tick 1', 'tick 2', 'tick 3']])
  })

  test('shows the end at once where the reader asks for reduced motion', async () => {
    browser.preference.value = 'reduce'
    const { log, sight }     = await played(2)

    sight.show(true)

    expect(log).toStrictEqual(['finish'])
  })

  test('leaves the widget where the reader left it once the last hold ends, motion reduced', async () => {
    browser.preference.value       = 'reduce'
    const { autoplay, log, sight } = await played(2)

    sight.show(true)
    autoplay.hold('keys', true)
    autoplay.hold('keys', false)

    expect(log).toStrictEqual(['finish'])
  })

  test('ends its timer when the widget unmounts', async () => {
    const { log, sight, unmount } = await played(5)

    sight.show(true)
    unmount()
    vi.advanceTimersByTime(1000)

    expect(log).toStrictEqual(['tick 1'])
  })
})
