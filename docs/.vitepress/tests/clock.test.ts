// @vitest-environment happy-dom
import { describe, expect, it, vi } from 'vitest'

import { stopped }                  from './common/clock.ts'

describe('stopped', { shuffle: false }, () => {
  stopped('fakes the timeouts, performance, and the animation frames before the case starts', () => {
    const fired: string[] = []
    const start           = performance.now()
    setTimeout(() => fired.push('timeout'), 10)
    clearTimeout(setTimeout(() => fired.push('cleared timeout'), 10))
    requestAnimationFrame(() => fired.push('frame'))
    cancelAnimationFrame(requestAnimationFrame(() => fired.push('canceled frame')))
    vi.advanceTimersByTime(20)

    expect([performance.now() - start, fired]).toStrictEqual([20, ['timeout', 'frame']])
  })

  it('leaves the case after it on the real clocks', () => {
    expect(vi.isFakeTimers()).toBe(false)
  })
})
