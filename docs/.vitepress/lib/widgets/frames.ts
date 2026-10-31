import { type MaybeElementRef, useElementVisibility, useRafFn } from '@vueuse/core'
import { type Ref, watch }                                      from 'vue'

import { useMotion } from './motion.ts'

/**
 * A canvas a widget draws into, before it mounts and once it has.
 */
export type Canvas = Ref<HTMLCanvasElement | undefined>

/**
 * What a canvas shows: the call that moves it `elapsed` milliseconds on and
 * reports whether it still moves, and the call that draws it.
 */
export interface Drawing {
  advance : (elapsed: number) => boolean
  draw    : (context: CanvasRenderingContext2D) => void
}

/**
 * The calls that draw onto a canvas, `paint` at once and `wake` on every frame
 * while something moves.
 */
export interface Painting {
  paint : () => void
  wake  : () => void
}

/**
 * The longest step one frame advances a drawing by, in milliseconds, which caps
 * the first frame after a tab returns from the background.
 */
const LONGEST = 64

/**
 * Draws `drawing` into `canvas` at once through `paint` and on every frame
 * while it moves once `wake` starts the loop, taking the canvas's context the
 * first time it draws.
 */
export function useCanvasLoop(canvas: Canvas, drawing: Drawing): Painting {
  let context: CanvasRenderingContext2D | null | undefined

  const paint = () => {
    context ??= canvas.value?.getContext('2d')
    if (context) drawing.draw(context)
  }

  const wake = useFrameLoop(canvas, elapsed => {
    const moving = drawing.advance(elapsed)
    paint()
    return moving
  })

  return { paint, wake }
}

/**
 * Draws a view once a frame while `advance` reports it still moving and
 * `target` shows on screen with motion playing, stopping once it settles.
 *
 * Returns:
 *   The call that starts the loop again once something moves.
 */
export function useFrameLoop(target: MaybeElementRef, advance: (elapsed: number) => boolean): () => void {
  const animate = useMotion()
  const visible = useElementVisibility(target)

  const loop = useRafFn(({ delta }) => {
    if (!advance(Math.min(LONGEST, delta))) loop.pause()
  }, { immediate: false })

  const wake = () => {
    if (visible.value && animate.value) loop.resume()
    else loop.pause()
  }

  watch([visible, animate], wake, { flush: 'sync' })

  return wake
}
