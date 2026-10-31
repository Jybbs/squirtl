import type { ReducedMotionType } from '@vueuse/core'
import { beforeEach, vi }         from 'vitest'
import { ref }                    from 'vue'

/**
 * A stand-in for the browser's `IntersectionObserver`, which happy-dom leaves
 * silent, so a case shows a widget on screen or hides it by calling `show`.
 */
export interface Sight {
  show: (seen: boolean) => void
}

/**
 * The reduced-motion preference the browser reports to every case, which a case
 * sets before it mounts a widget and which starts each case at `no-preference`,
 * the answer happy-dom gives.
 */
export const preference = ref<ReducedMotionType>('no-preference')

vi.mock('@vueuse/core', async original => ({
  ...await original<typeof import('@vueuse/core')>(),
  usePreferredReducedMotion: () => preference
}))

beforeEach(() => {
  preference.value = 'no-preference'
})

/**
 * Stubs the global observer `name` names with one that hands every entry a case
 * reports to each callback it was given, and returns the call that reports one.
 */
function stubObserver<Entry>(name: 'IntersectionObserver' | 'ResizeObserver'): (entry: Entry) => void {
  const callbacks: ((entries: Entry[], observer: never) => void)[] = []
  vi.stubGlobal(name, class {
    constructor(callback: (entries: Entry[], observer: never) => void) {
      callbacks.push(callback)
    }

    disconnect() {}

    observe() {}

    unobserve() {}
  })
  return entry => {
    for (const callback of callbacks) callback([entry], {} as never)
  }
}

/**
 * Stubs the global `IntersectionObserver` with one that reports to every
 * callback it was handed whenever a case calls `show`.
 */
export function stubSight(): Sight {
  const report = stubObserver<IntersectionObserverEntry>('IntersectionObserver')
  return { show: seen => report({ isIntersecting: seen, time: 0 } as IntersectionObserverEntry) }
}

/**
 * Stubs the global `ResizeObserver` with one that reports a box `width` by
 * `height` pixels to every callback it was handed whenever a case calls the
 * function this returns.
 */
export function stubSize(): (width: number, height: number) => void {
  const report = stubObserver<ResizeObserverEntry>('ResizeObserver')
  return (width, height) => report({ contentRect: { height, width } } as ResizeObserverEntry)
}
