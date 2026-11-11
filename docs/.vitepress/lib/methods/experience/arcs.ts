import { useTransition }         from '@vueuse/core'
import type { ComputedRef, Ref } from 'vue'

import * as experience from '../experience.ts'

/**
 * Eases each arc of the batch from where the last update's landed to the step
 * the update `ages` names reads, one after another, newest first, on the
 * identity's curve, every arc landing at once while `still` holds.
 */
export function useArcs(ages: ComputedRef<readonly number[]>, still: Ref<boolean>): Ref<number>[] {
  return Array.from({ length: experience.MEMORY.batch }, (_, i) => useTransition(() => ages.value[i]!, {
    delay    : i * experience.STEP,
    disabled : still,
    duration : 4 * experience.STEP,
    easing   : [...experience.CURVE] as [number, number, number, number]
  }))
}
