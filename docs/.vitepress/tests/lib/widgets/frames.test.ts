// @vitest-environment happy-dom
import { enableAutoUnmount, mount }                          from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { defineComponent, h, nextTick, ref }                 from 'vue'

import { useFrameLoop }          from '../../../lib/widgets/frames.ts'
import { preference, stubSight } from '../../common/browser.ts'

/**
 * Mounts a drawing that moves for `frames` frames, recording the step each
 * frame advanced it by, and returns that record beside the call waking the loop
 * and the sight a case shows it through.
 */
async function drawn(frames: number) {
  const sight           = stubSight()
  const steps: number[] = []
  let wake!: () => void
  mount(defineComponent({
    setup: () => {
      const node = ref<HTMLElement>()
      wake = useFrameLoop(node, elapsed => {
        steps.push(elapsed)
        return steps.length < frames
      })
      return () => h('canvas', { ref: node })
    }
  }))
  await nextTick()
  return { sight, steps, wake }
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['performance', 'requestAnimationFrame', 'cancelAnimationFrame'] })
})

enableAutoUnmount(afterEach)

describe('useFrameLoop', () => {
  test('draws a frame at a time while the drawing shows and moves, and stops once it settles', async () => {
    const { sight, steps } = await drawn(3)

    sight.show(true)
    vi.advanceTimersByTime(1000)

    expect(steps).toHaveLength(3)
    expect(Math.max(...steps)).toBeLessThanOrEqual(64)
  })

  test('draws nothing off screen or under reduced motion, until woken on screen with motion', async () => {
    preference.value             = 'reduce'
    const { sight, steps, wake } = await drawn(2)

    sight.show(true)
    vi.advanceTimersByTime(500)
    const still      = steps.length
    preference.value = 'no-preference'
    await nextTick()
    wake()
    vi.advanceTimersByTime(500)

    expect([still, steps.length]).toStrictEqual([0, 2])
  })
})
