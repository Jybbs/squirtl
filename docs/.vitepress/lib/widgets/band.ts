import { clamp }                   from '@vueuse/core'
import { type Ref, computed, ref } from 'vue'

import type { Scrub } from './scrub.ts'

/**
 * A drawing a pointer presses or drags across to pick a position directly:
 * the slider's control with Zag.js's own press replaced by one picking the
 * position under the pointer, and the thumb that press moves focus to.
 */
export interface Band {
  control : Scrub['control']
  thumb   : Ref<HTMLElement | undefined>
}

/**
 * Turns the control of `scrub` into a band where the position under a pointer
 * is the one `pick` reads from it, rather than one along a single axis, a press
 * capturing the pointer and moving focus to the band's thumb, and a drag with
 * a button held picking again as it moves.
 */
export function useBand(scrub: Scrub, pick: (event: PointerEvent) => void): Band {
  const thumb   = ref<HTMLElement>()
  const control = computed(() => ({
    ...scrub.control.value,
    onPointerdown: (event: PointerEvent) => {
      (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
      thumb.value!.focus({ preventScroll: true })
      pick(event)
    },
    onPointermove: (event: PointerEvent) => { if (event.buttons) pick(event) }
  }))

  return { control, thumb }
}

/**
 * Reads the cell of a grid of `columns` by `rows` laid over the element a
 * pointer `event` lands on, the nearest edge cell where the pointer has been
 * dragged past an edge.
 */
export function cellAt(event: PointerEvent, columns: number, rows: number): readonly [column: number, row: number] {
  const { height, left, top, width } = (event.currentTarget as HTMLElement).getBoundingClientRect()
  return [
    clamp(Math.floor((event.clientX - left) / width * columns), 0, columns - 1),
    clamp(Math.floor((event.clientY - top) / height * rows), 0, rows - 1)
  ]
}
