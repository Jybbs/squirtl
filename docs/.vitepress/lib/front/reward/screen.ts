import type { MaybeElementRef } from '@vueuse/core'
import { onMounted, ref }       from 'vue'

import { type Canvas, useCanvasLoop } from '../../widgets/frames.ts'
import { useMotion }                  from '../../widgets/motion.ts'
import { type Playback, useScrub }    from '../../widgets/scrub.ts'
import * as reward                    from '../reward.ts'

/**
 * The name a screen reader reads for the climb the widget's slider runs along.
 */
const SLIDER = 'The return across the episode, which shows the screen at any step it points to'

/**
 * Draws the screen of `showing` into `canvas` once it mounts, again once the
 * rooms' images load, and again while its glide or its fade runs.
 *
 * Returns:
 *   The call that shows the step the player stands at, gliding to it over
 *   the milliseconds it takes where motion plays and setting it at once where
 *   the reader asks for reduced motion.
 */
function useScreen(canvas: Canvas, showing: reward.Showing): (span: number) => void {
  const animate         = useMotion()
  const { paint, wake } = useCanvasLoop(canvas, {
    advance : elapsed => showing.screen.advance(elapsed),
    draw    : context => showing.screen.draw(context)
  })

  onMounted(() => {
    paint()
    showing.images.whenReady(paint)
  })

  return span => {
    if (!animate.value) {
      showing.screen.snap()
      paint()
      return
    }
    showing.screen.follow(span)
    wake()
  }
}

/**
 * Plays the episode of `showing` on its screen in `canvas` while the widget at
 * `root` shows on screen, the screen gliding to each step, and makes the climb
 * the slider over its steps, which shows the screen and the figures at the step
 * it points to.
 */
export function useEpisode(canvas: Canvas, root: MaybeElementRef, showing: reward.Showing): Playback {
  const at                = ref(0)
  const glide             = useScreen(canvas, showing)
  const { player, trace } = showing

  const show = (span: number) => {
    at.value = player.episode.steps
    glide(span)
  }

  const scrub = useScrub(root, reward.playingOf(player, show), {
    at       : at,
    count    : trace.length,
    describe : step => reward.describeStep(trace, step),
    label    : SLIDER,
    seek     : step => {
      player.seek(step)
      show(0)
    }
  })

  return { at, scrub }
}
