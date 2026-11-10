import { clamp }                                from '@vueuse/core'
import { type ComputedRef, type Ref, computed } from 'vue'

import type { Scrub } from './scrub.ts'

/**
 * A drawing a pointer presses or drags across to pick a position directly,
 * the slider's control with Zag.js's own press left out, and the handlers that
 * take its place.
 */
export interface Band {
  control : ComputedRef<Record<string, unknown>>
  point   : (event: PointerEvent) => void
  press   : (event: PointerEvent) => void
}

/**
 * Turns the control of `scrub` into a band where the position under a pointer
 * is the one `pick` reads from it, rather than one along a single axis, a press
 * capturing the pointer and moving focus to the slider's `thumb`.
 */
export function useBand(scrub: Scrub, thumb: Ref<HTMLElement | undefined>, pick: (event: PointerEvent) => void): Band {
  const control = computed(() => {
    const { onPointerdown: _, ...rest } = scrub.control.value as typeof scrub.control.value & { onPointerdown: unknown }
    return rest
  })

  const press = (event: PointerEvent) => {
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
    thumb.value!.focus({ preventScroll: true })
    pick(event)
  }

  return { control, point: pick, press }
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
