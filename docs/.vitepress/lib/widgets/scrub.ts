import type { MaybeElementRef }                        from '@vueuse/core'
import * as slider                                     from '@zag-js/slider'
import { type PropTypes, normalizeProps, useMachine }  from '@zag-js/vue'
import { type ComputedRef, type Ref, computed, useId } from 'vue'

import { type Ticking, useAutoplay } from './autoplay.ts'

/**
 * The position a widget's clock stands at and the slider its drawing makes of
 * it.
 */
export interface Playback {
  at    : Ref<number>
  scrub : Scrub
}

/**
 * The props one part of the slider takes, as the Vue adapter writes them.
 */
type Props = ReturnType<slider.Api<PropTypes>['getRootProps']>

/**
 * The props a drawing spreads onto itself and onto the focusable thumb laid
 * over it.
 */
export interface Scrub {
  control : ComputedRef<Props>
  root    : ComputedRef<Props>
  thumb   : ComputedRef<Props>
}

/**
 * What a drawing that serves as its own slider needs, its positions, the name
 * and the description a screen reader reads, the position it shows, and the
 * call that seeks a position.
 */
export interface Scrubbing {
  at       : Ref<number>
  count    : number
  describe : (at: number) => string
  label    : string
  seek     : (at: number) => void
}

/**
 * Reports whether `event` comes from a mouse.
 */
export const fromMouse = (event: PointerEvent): boolean => event.pointerType === 'mouse'

/**
 * Makes a drawing its own slider on Zag.js's slider machine, which holds the
 * position, its ARIA attributes, and its keys, and steps `ticking` through an
 * autoplay while the widget at `target` shows. The position moves only through
 * the keys, a press or a drag along the drawing, or the thumb, never under a
 * mouse resting on the drawing or moving across it, which holds the autoplay
 * instead, as the thumb's focus does. Each part leaves off the inline style the
 * machine sets, so its look comes from its classes alone.
 */
export function useScrub(target: MaybeElementRef, ticking: Ticking, scrubbing: Scrubbing): Scrub {
  const { at, count, describe, label, seek } = scrubbing
  const { hold }                             = useAutoplay(target, ticking)
  const id                                   = useId()
  const service                              = useMachine(slider.machine, computed(() => ({
    'aria-label'     : [label],
    getAriaValueText : ({ value }: slider.ValueTextDetails) => describe(value),
    id               : id,
    max              : count - 1,
    min              : 0,
    onFocusChange    : ({ focusedIndex }: slider.FocusChangeDetails) => hold('keys', focusedIndex !== -1),
    onValueChange    : ({ value }: slider.ValueChangeDetails) => seek(value[0]!),
    value            : [at.value]
  })))
  const api = computed(() => slider.connect(service, normalizeProps))

  return {
    root    : computed(() => ({ ...api.value.getRootProps(), style: undefined })),
    thumb   : computed(() => ({ ...api.value.getThumbProps({ index: 0 }), style: undefined })),
    control : computed(() => ({
      ...api.value.getControlProps(),
      onPointerenter : (event: PointerEvent) => { if (fromMouse(event)) hold('pointer', true) },
      onPointerleave : (event: PointerEvent) => { if (fromMouse(event)) hold('pointer', false) },
      style          : undefined
    }))
  }
}
