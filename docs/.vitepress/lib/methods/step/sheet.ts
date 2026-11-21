import { type Ref, onMounted } from 'vue'

import { Episode }            from '../../game/episode.ts'
import { RoomImages }         from '../../game/images.ts'
import { GameScreen, SCREEN } from '../../game/screen.ts'
import * as step              from '../step.ts'

/**
 * The pixels from one cell's corner to the next, and the sheet's width and
 * height.
 */
export const PITCH  = step.SHEET.cell + step.SHEET.gap
export const WIDTH  = step.FRAMES * PITCH
export const HEIGHT = step.STEPS.length * PITCH

/**
 * Draws every frame of every step into `canvas`, each cell the part of the
 * bedroom's screen round Blue as pret/pokered draws it on that frame, leaving
 * the canvas blank where it gives no 2D context.
 */
function paintSheet(canvas: HTMLCanvasElement, images: RoomImages): void {
  const episode = new Episode()
  const screen  = new GameScreen(episode, images)
  const source  = Object.assign(document.createElement('canvas'), SCREEN).getContext('2d')
  const context = canvas.getContext('2d')
  const { cell, crop, gap } = step.SHEET
  if (!source || !context) return
  episode.at                    = step.START.at
  context.imageSmoothingEnabled = false
  step.STEPS.forEach((each, s) => each.frames.forEach((frame, f) => {
    screen.view.at.splice(0, 2, ...step.viewAt(each, f + 1))
    episode.facing = frame.facing
    screen.stance  = frame.stance
    screen.draw(source)
    const [x, y] = [f * PITCH + gap / 2, s * PITCH + gap / 2]
    context.drawImage(source.canvas, crop[0], crop[1], cell, cell, x, y, cell, cell)
  }))
}

/**
 * Paints the sheet into `canvas` once the widget mounts and the bedroom's
 * image can draw.
 */
export function useSheet(canvas: Ref<HTMLCanvasElement | undefined>): void {
  onMounted(() => {
    const images = new RoomImages()
    images.whenReady(() => paintSheet(canvas.value!, images), ['bedroom'])
  })
}
