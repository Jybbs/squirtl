import { usePreferredReducedMotion }  from '@vueuse/core'
import { type ComputedRef, computed } from 'vue'

import { IDENTITY } from '../identity/identity.ts'

/**
 * The beat a motion counts in, the identity's step, and the easing a glide
 * takes, CSS's `ease-in-out`, as the tuple `useTransition` reads.
 */
export const BEAT   = IDENTITY.motion.duration
export const TRAVEL = [...IDENTITY.motion.travel] as [number, number, number, number]

/**
 * Reads whether the page plays motion, which it does unless the reader's system
 * reports `prefers-reduced-motion: reduce`.
 */
export function useMotion(): ComputedRef<boolean> {
  const preference = usePreferredReducedMotion()
  return computed(() => preference.value !== 'reduce')
}
