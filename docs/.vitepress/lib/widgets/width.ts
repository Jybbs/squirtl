import { type MaybeElementRef, useElementSize } from '@vueuse/core'
import { type ComputedRef, computed }           from 'vue'

import { IDENTITY } from '../identity/identity.ts'

/**
 * Measures the width a drawing takes in `target` in whole pixels, no narrower
 * than `least`, reading the width of a plate before `target` is measured.
 */
export function useDrawnWidth(target: MaybeElementRef, least: number): ComputedRef<number> {
  const { width } = useElementSize(target, { height: 0, width: IDENTITY.lengths.plate })
  return computed(() => Math.max(least, Math.round(width.value)))
}
