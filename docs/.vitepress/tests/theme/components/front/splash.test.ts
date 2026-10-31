// @vitest-environment happy-dom
import { enableAutoUnmount, mount }                          from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { nextTick, ref }                                     from 'vue'

import { TONES }              from '../../../../lib/front/sky.ts'
import * as browser           from '../../../common/browser.ts'
import { Recorder, drawInto } from '../../../common/canvas.ts'

const dark = ref(false)

vi.mock('vitepress', () => ({ useData: () => ({ isDark: dark }) }))

const { Splash } = await import('../../../../theme/components/front/splash.tsx')

/**
 * Mounts the splash over a page 2,000 pixels tall with one paragraph of words,
 * its canvas drawing into a recorder, and returns the recorder beside the sight
 * that shows the splash on screen.
 */
async function splashed(): Promise<{ recorder: Recorder, sight: browser.Sight }> {
  const recorder = drawInto(new Recorder())
  const sight    = browser.stubSight()
  vi.spyOn(document.documentElement, 'scrollHeight', 'get').mockReturnValue(2000)
  vi.spyOn(document.documentElement, 'clientWidth', 'get').mockReturnValue(840)
  document.body.innerHTML = '<div class="vp-doc"><p>Words.</p></div>'
  mount(Splash, { attachTo: document.body })
  await nextTick()
  return { recorder, sight }
}

beforeEach(() => {
  dark.value               = false
  browser.preference.value = 'reduce'
})

enableAutoUnmount(afterEach)

afterEach(() => {
  document.body.innerHTML = ''
})

describe('Splash', () => {
  test('draws the whole walk still in the light tones where the reader asks for reduced motion', async () => {
    const { recorder } = await splashed()

    expect(recorder.arcs.length).toBeGreaterThan(0)
    expect(new Set(recorder.arcs.map(arc => arc.fill))).toStrictEqual(new Set([TONES.light.dot]))
  })

  test('draws again in the dark tones when the reader switches the scheme', async () => {
    const { recorder } = await splashed()

    dark.value = true
    await nextTick()

    expect(new Set(recorder.arcs.map(arc => arc.fill))).toStrictEqual(new Set([TONES.dark.dot]))
  })

  test('draws again as the reader scrolls with motion off', async () => {
    const { recorder } = await splashed()
    recorder.arcs      = []

    window.dispatchEvent(new Event('scroll'))

    expect(recorder.arcs.length).toBeGreaterThan(0)
  })

  test('flickers the walk a frame at a time once the splash shows with motion playing', async () => {
    vi.useFakeTimers({ toFake: ['requestAnimationFrame', 'performance'] })
    browser.preference.value  = 'no-preference'
    const { recorder, sight } = await splashed()
    recorder.arcs             = []

    sight.show(true)
    window.dispatchEvent(new Event('scroll'))
    vi.advanceTimersByTime(100)

    expect(recorder.arcs.length).toBeGreaterThan(0)
  })
})
