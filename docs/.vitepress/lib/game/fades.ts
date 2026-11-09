import { type ShallowRef, onMounted, shallowRef } from 'vue'

import WORLD                           from '../art/world.json' with { type: 'json' }
import { RoomImages }                  from './images.ts'
import { packedAt, recolor, shadesOf } from './palettes.ts'
import type { Place }                  from './rooms.ts'
import { SQUARE }                      from './screen.ts'

/**
 * A room's image in each palette of a fade, beside each the same image with
 * its lightest color left clear, the pixels the grass draws over a sprite's
 * lower half, and the room's colors from the lightest.
 */
export interface Faded {
  map    : HTMLCanvasElement[]
  over   : HTMLCanvasElement[]
  shades : number[]
}

/**
 * The part of an image a fade renders, in the image's pixels.
 */
export interface Crop {
  height : number
  width  : number
  x      : number
  y      : number
}

/**
 * Renders the `part` of `image`, the whole image unless given one, in
 * every palette of `palettes`, each pixel's color mapped through the palette as
 * `rBGP` maps a color, or nothing where the canvas gives no 2D context.
 */
export function fadedOf(
  image    : HTMLImageElement,
  palettes : readonly string[],
  part?    : Crop
): Faded | null {
  const crop    = part ?? { height: image.naturalHeight, width: image.naturalWidth, x: 0, y: 0 }
  const size    = { height: crop.height, width: crop.width }
  const context = Object.assign(document.createElement('canvas'), size).getContext('2d', { willReadFrequently: true })
  if (!context) return null
  context.drawImage(image, crop.x, crop.y, crop.width, crop.height, 0, 0, crop.width, crop.height)
  const pixels = context.getImageData(0, 0, size.width, size.height).data
  const shades = shadesOf(pixels)
  const render = (palette: string, clear: boolean) => {
    const canvas = Object.assign(document.createElement('canvas'), size)
    const out    = new ImageData(size.width, size.height)
    recolor(palette, shades, pixels, out.data)
    if (clear) {
      for (let at = 0; at < pixels.length; at += 4) {
        if (packedAt(pixels, at) === shades[0]) out.data[at + 3] = 0
      }
    }
    canvas.getContext('2d')?.putImageData(out, 0, 0)
    return canvas
  }
  return { map: palettes.map(palette => render(palette, false)), over: palettes.map(palette => render(palette, true)), shades }
}

/**
 * Renders every room's map, its padding cropped away, in each palette of
 * `palettes` once the rooms' images load, the map empty until they do.
 */
export function useRoomFades(palettes: readonly string[]): ShallowRef<ReadonlyMap<Place, Faded>> {
  const images = new RoomImages()
  const rooms  = shallowRef<ReadonlyMap<Place, Faded>>(new Map())
  onMounted(() => images.whenReady(() => {
    rooms.value = new Map((Object.keys(WORLD) as Place[]).flatMap(place => {
      const { h, pad, w } = WORLD[place]
      const faded         = fadedOf(images.image(place), palettes, { height: h * SQUARE, width: w * SQUARE, x: pad * SQUARE, y: pad * SQUARE })
      return faded ? [[place, faded] as const] : []
    }))
  }))
  return rooms
}
