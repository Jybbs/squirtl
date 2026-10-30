import { usePreferredReducedMotion }  from '@vueuse/core'
import { type ComputedRef, computed } from 'vue'

/**
 * Reads whether the page plays motion, which it does unless the reader's system
 * reports `prefers-reduced-motion: reduce`.
 */
export function useMotion(): ComputedRef<boolean> {
  const preference = usePreferredReducedMotion()
  return computed(() => preference.value !== 'reduce')
}
