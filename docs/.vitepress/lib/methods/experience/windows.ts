import { refDebounced } from '@vueuse/core'
import { type ComputedRef, type Ref, computed, onMounted, ref, watch } from 'vue'

import { Episode }                    from '../../game/episode.ts'
import { RoomImages }                 from '../../game/images.ts'
import { GameScreen, SCREEN, SQUARE } from '../../game/screen.ts'
import * as experience                from '../experience.ts'

/**
 * The step each window shows, its age and the place of its arc in the batch,
 * beside the canvases the windows draw into.
 */
export interface Windows {
  canvases : Ref<HTMLCanvasElement[]>
  shown    : Ref<{ age: number, i: number }>[]
}

/**
 * The left and top of the part of the game screen a window shows, the three
 * squares by three round Blue, who stands on the screen's fifth column and row.
 */
const CROP = { left: 3 * SQUARE, top: 3 * SQUARE } as const

/**
 * Draws the step `shown` into the window `canvas`, painting the screen round
 * Blue through `screen` into `source` and copying the three squares round him,
 * leaving the window blank where either gives no 2D context.
 */
function paintWindow(canvas: HTMLCanvasElement, shown: experience.Shown, screen: GameScreen, source: CanvasRenderingContext2D | null): void {
  const context = canvas.getContext('2d')
  if (!source || !context) return
  Object.assign(screen.episode, { at: shown.at, chosen: shown.chosen, facing: shown.facing, leader: null, place: shown.place })
  screen.snap()
  screen.draw(source)
  context.imageSmoothingEnabled = false
  context.drawImage(source.canvas, CROP.left, CROP.top, experience.WINDOW, experience.WINDOW, 0, 0, experience.WINDOW, experience.WINDOW)
}

/**
 * Shows the step under every fourth arc of the update `ages` names in a window,
 * each window following its arc once the arc lands, at once where `motion` is
 * off, and draws each step once the rooms load.
 */
export function useWindows(ages: ComputedRef<readonly number[]>, motion: Ref<boolean>): Windows {
  const canvases = ref<HTMLCanvasElement[]>([])
  const shown    = Array.from({ length: experience.MEMORY.batch / experience.EVERY }, (_, n) => {
    const i = n * experience.EVERY
    return refDebounced(computed(() => ({ age: ages.value[i]!, i })), () => motion.value ? i * experience.STEP : 0)
  })
  const images = new RoomImages()
  const screen = new GameScreen(new Episode(), images)
  let ready    = false
  let source: CanvasRenderingContext2D | null = null

  const paint = () => {
    if (!ready) return
    shown.forEach((each, n) => {
      const canvas = canvases.value[n]
      if (canvas) paintWindow(canvas, experience.shownOf(each.value.age, each.value.i), screen, source)
    })
  }

  watch(shown, paint)
  onMounted(() => images.whenReady(() => {
    source = Object.assign(document.createElement('canvas'), SCREEN).getContext('2d')
    ready  = true
    paint()
  }))
  return { canvases, shown }
}
