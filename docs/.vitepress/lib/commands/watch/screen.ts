import { type Ref, onMounted, watch } from 'vue'

import { RoomImages }         from '../../game/images.ts'
import { paintGround }        from '../../game/palettes.ts'
import { Player }             from '../../game/player.ts'
import { GameScreen, SCREEN } from '../../game/screen.ts'
import * as watching          from '../watch.ts'

/**
 * Draws PyBoy's window onto `canvas` at the time `t` and the step `step` reach
 * once the rooms load, the ground alone until the intro checks the digest,
 * then the episode played to the step under the veil the reset lifts.
 */
export function useWatchScreen(canvas: Ref<HTMLCanvasElement | undefined>, t: Ref<number>, step: Ref<number>): void {
  const images = new RoomImages()
  const player = new Player()
  const screen = new GameScreen(player.episode, images)
  let ready    = false

  const paint = () => {
    const context = canvas.value?.getContext('2d')
    if (!ready || !context) return
    if (t.value < watching.PHASES.digest) {
      paintGround(context, SCREEN.width, SCREEN.height)
      return
    }
    if (player.episode.steps > step.value) player.reset()
    player.playTo(step.value)
    screen.snap()
    screen.veil = watching.veilAt(t.value)
    screen.draw(context)
  }

  watch([step, () => t.value < watching.PHASES.reset && t.value], paint)
  onMounted(() => images.whenReady(() => {
    ready = true
    paint()
  }))
}
