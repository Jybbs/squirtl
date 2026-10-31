import { onMounted, watch } from 'vue'

import { frameFor }                                  from '../game/actors.ts'
import { RoomImages }                                from '../game/images.ts'
import { PLAIN, colorOf, recolor, shadesOf }         from '../game/palettes.ts'
import * as screen                                   from '../game/screen.ts'
import { paintBox, paintText }                       from '../game/text.ts'
import { type Canvas, type Painting, useCanvasLoop } from '../widgets/frames.ts'
import { useMotion }                                 from '../widgets/motion.ts'
import * as city                                     from './city.ts'
import * as warp                                     from './warp.ts'

/**
 * The canvas members a Glitch City is drawn through and read back from in
 * every palette of the warp.
 */
export type CityReader = Pick<
  CanvasRenderingContext2D,
  'createImageData' | 'drawImage' | 'fillRect' | 'fillStyle' | 'getImageData'
>

/**
 * The canvas members a frame of the warp is drawn through.
 */
export type WarpPainter = Pick<CanvasRenderingContext2D, 'fillRect' | 'fillStyle' | 'putImageData'>

/**
 * The text box pret/pokered's `DisplayWildLocations` draws on the Pokédex's
 * area screen when it finds no nest, 17 tiles by 4 from column 1 with
 * AREA UNKNOWN printed a column in and two rows down
 * (`engine/items/town_map.asm` lines 403 to 409 and 421 to 422), set six rows
 * lower than the area screen sets it so it clears Blue at the screen's middle.
 */
const UNKNOWN = {
  box  : { column: 1, columns: 17, row: 13, rows: 4 },
  text : ' AREA UNKNOWN',
  x    : 16,
  y    : 120
}

/**
 * Blue alone in the Glitch City a missing address reads as, playing the warp
 * `frames` holds frame by frame on the Game Boy's clock, the city drawn in
 * each palette of the warp once it is read and Blue drawn over it while the
 * screen shows its own shades.
 */
export class GlitchScreen {
  readonly #frames : readonly warp.WarpFrame[]
  #elapsed         = 0
  #palettes        : ReadonlyMap<string, ImageData> | null = null

  constructor(frames: readonly warp.WarpFrame[] = warp.warpLoop) {
    this.#frames = frames
  }

  /**
   * Reads the frame of the warp the screen shows.
   */
  get frame(): warp.WarpFrame {
    return this.#frames[Math.floor(this.#elapsed / screen.FRAME) % this.#frames.length]!
  }

  /**
   * Moves the warp `elapsed` milliseconds on, and reports whether it still
   * plays, which it does on a loop once the city is drawn.
   */
  advance(elapsed: number): boolean {
    if (!this.#palettes) return false
    this.#elapsed += elapsed
    return true
  }

  /**
   * Draws the frame of the warp the screen shows, the city in the frame's
   * palette and Blue at the frame's facing and height while the screen shows
   * its own shades and he stands below its top.
   */
  draw(context: WarpPainter): void {
    const { facing, palette, y } = this.frame
    const shaded                 = this.#palettes?.get(palette)
    if (!shaded) return
    context.putImageData(shaded, 0, 0)
    if (palette === PLAIN && y > warp.Y.gone) {
      screen.paintSprite(context, frameFor('player', facing), screen.CENTER * screen.SQUARE, y)
    }
  }

  /**
   * Draws the Glitch City `address` reads as onto `reader`, each place taking
   * the block of `blocks` its byte picks from `image`, Pallet Town's image, with
   * the AREA UNKNOWN box over its foot, and reads it back in every palette of
   * the warp.
   */
  read(reader: CityReader, image: CanvasImageSource, blocks: readonly city.Origin[], address: string): void {
    const { height, width } = screen.SCREEN
    city.paintCity(reader, image, address, blocks)
    const shades = shadesOf(reader.getImageData(0, 0, width, height).data)
    const inks   = shades.map(shade => colorOf(shade))
    paintBox(reader, UNKNOWN.box, inks)
    paintText(reader, UNKNOWN.text, UNKNOWN.x, UNKNOWN.y, inks)
    const base     = reader.getImageData(0, 0, width, height)
    this.#palettes = new Map(warp.FADE.map(palette => {
      const shaded = reader.createImageData(width, height)
      recolor(palette, shades, base.data, shaded.data)
      return [palette, shaded] as const
    }))
  }

  /**
   * Sets the warp back to its first frame, Blue standing on his square facing
   * down.
   */
  reset(): void {
    this.#elapsed = 0
  }
}

/**
 * Reads the pixels of `image` through a canvas of its own size, or `null` where
 * the document gives that canvas no context to draw through.
 */
function pixelsOf(image: HTMLImageElement): ImageData | null {
  const { naturalHeight: height, naturalWidth: width } = image
  const context = Object.assign(document.createElement('canvas'), { height, width })
    .getContext('2d', { willReadFrequently: true })
  context?.drawImage(image, 0, 0)
  return context?.getImageData(0, 0, width, height) ?? null
}

/**
 * Draws the Glitch City `address` reads as onto `canvas` once Pallet Town's
 * image can draw, playing the warp on a loop while the canvas shows and motion
 * plays and standing Blue still facing down where motion stops, and draws
 * nothing where the image fails to decode.
 */
export function useGlitchCity(canvas: Canvas, address: () => string): Painting {
  const images   = new RoomImages()
  const glitch   = new GlitchScreen()
  const animate  = useMotion()
  const painting = useCanvasLoop(canvas, glitch)

  watch(animate, plays => {
    if (plays) return
    glitch.reset()
    painting.paint()
  })

  onMounted(() => images.whenReady(() => {
    const context = canvas.value?.getContext('2d', { willReadFrequently: true })
    const image   = images.image('pallet')
    const pixels  = pixelsOf(image)
    if (!context || !pixels) return
    glitch.read(context, image, city.blocksOf(pixels), address())
    painting.paint()
    painting.wake()
  }, ['pallet']))

  return painting
}
