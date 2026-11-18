import { afterEach, test, vi } from 'vitest'

afterEach(() => {
  vi.useRealTimers()
})

/**
 * A case run on a stopped clock, which fakes the timeouts, `performance`, and
 * the animation frames before the case starts, so the case moves a widget's
 * beats and frame loop through `vi.advanceTimersByTime`.
 */
export const stopped = test.extend('clock', { auto: true }, () => {
  vi.useFakeTimers({
    toFake: ['setTimeout', 'clearTimeout', 'performance', 'requestAnimationFrame', 'cancelAnimationFrame']
  })
})
