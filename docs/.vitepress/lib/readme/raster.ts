import { Resvg } from '@resvg/resvg-js'

import WORLD                from '../art/world.json' with { type: 'json' }
import { facesOf }          from '../cards/render.ts'
import * as transition      from '../front/learning/transition.ts'
import type { TownPainter } from '../front/learning/walks.ts'
import { SQUARE }           from '../game/screen.ts'
import { rgbOf }            from '../identity/identity.ts'

/**
 * Makes a blank view of `width` by `height` pixels, every pixel clear, in the
 * shape a canvas reads one back.
 */
function blankView(width: number, height: number): ImageData {
  return { colorSpace: 'srgb', data: new Uint8ClampedArray(width * height * 4), height, width }
}

/**
 * Reads the RGBA pixels of `svg` as the renderer draws it, setting its words in
 * the faces under the checkout `metaUrl` names.
 */
export function svgPixels(metaUrl: string, svg: string): Uint8Array {
  return new Resvg(svg, { font: facesOf(metaUrl) }).render().pixels
}

/**
 * Reads the town's view of `view` out of Pallet Town's image in every palette
 * the transition shows, the image drawn at its own pixels with the view's top
 * left at the corner.
 */
export function townIn(metaUrl: string, view: transition.TownView): transition.Town {
  const { h, image, pad, w } = WORLD.pallet
  const [left, top]          = transition.viewCorner(view)
  const base                 = blankView(view.width, view.height)
  base.data.set(svgPixels(metaUrl,
    `<svg xmlns="http://www.w3.org/2000/svg" width="${view.width}" height="${view.height}">`
    + `<image href="${image.light}" x="${-left}" y="${-top}" `
    + `width="${(w + 2 * pad) * SQUARE}" height="${(h + 2 * pad) * SQUARE}"/></svg>`))
  return transition.townOf(base, blankView, view)
}

/**
 * A grid of pixels a drawing paints through the canvas members the town's walks
 * call, outside any browser, each fill blended over what lies under it at the
 * opacity `globalAlpha` holds.
 */
export class Raster implements TownPainter {
  fillStyle             = '#000000'
  globalAlpha           = 1
  imageSmoothingEnabled = false

  readonly view: ImageData

  constructor(width: number, height: number) {
    this.view = blankView(width, height)
  }

  /**
   * Fills the rectangle of `width` by `height` pixels with its top left at `x`
   * and `y` in `fillStyle`, leaving out what falls past the grid's edges.
   */
  fillRect(x: number, y: number, width: number, height: number): void {
    const { data, height: rows, width: columns } = this.view
    const fill                                   = rgbOf(this.fillStyle)
    const alpha                                  = this.globalAlpha
    const left                                   = Math.max(0, Math.round(x))
    const right                                  = Math.min(columns, Math.round(x + width))
    const top                                    = Math.max(0, Math.round(y))
    const bottom                                 = Math.min(rows, Math.round(y + height))
    for (let row = top; row < bottom; row++) {
      for (let at = 4 * (row * columns + left); at < 4 * (row * columns + right); at += 4) {
        for (const [channel, value] of fill.entries()) {
          data[at + channel] = data[at + channel]! + (value - data[at + channel]!) * alpha
        }
        data[at + 3] = 255
      }
    }
  }

  /**
   * Copies every pixel of `image` onto the grid with its top left at `x` and
   * `y`, which a view the grid's own size fills whole from its corner.
   */
  putImageData(image: ImageData, x: number, y: number): void {
    for (let row = 0; row < image.height; row++) {
      const from = row * image.width * 4
      const to   = ((row + y) * this.view.width + x) * 4
      this.view.data.set(image.data.subarray(from, from + image.width * 4), to)
    }
  }
}
