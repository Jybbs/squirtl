import { createRequire } from 'node:module'

import type * as gifenc from 'gifenc'

/**
 * One frame as the GIF holds it, the milliseconds it shows and the palette
 * index of each pixel, row by row.
 */
interface Held {
  delay   : number
  indices : Uint8Array
}

/**
 * A looping animation as the GIF encoder reads it, its size in pixels, the
 * milliseconds each frame holds, and its frames in order, each pixel a color's
 * red, green, and blue bytes as one number, row by row. `frames` is read twice,
 * once for the palette and once for the frames themselves, so each read yields
 * the same frames, and each frame is read before the next, which may be drawn
 * into the same array.
 */
export interface Movie {
  delay  : number
  frames : () => Iterable<Uint32Array>
  height : number
  width  : number
}

/**
 * The palette index every frame leaves clear, so the frame before shows
 * through it, one past the 255 colors the palette holds.
 */
const CLEAR = 255

/**
 * Loads `gifenc` through `require`, since its CommonJS build defines each
 * export through a getter Node's named-export detection does not read, and its
 * ES module build sits in a `.js` file Node loads as CommonJS.
 */
const { GIFEncoder, nearestColorIndex } = createRequire(import.meta.url)('gifenc') as typeof gifenc

/**
 * Reads each frame of `movie` beside the pixels it changes from the frame
 * before, every pixel on the first frame.
 */
function* changesOf(movie: Movie): Generator<[frame: Uint32Array, changed: number[]]> {
  const shown = new Uint32Array(movie.width * movie.height)
  let first   = true
  for (const frame of movie.frames()) {
    const changed = []
    for (let pixel = 0; pixel < frame.length; pixel++) {
      if (first || frame[pixel] !== shown[pixel]) changed.push(pixel)
    }
    shown.set(frame)
    first = false
    yield [frame, changed]
  }
}

/**
 * Splits `color` into its red, green, and blue bytes.
 */
const channelsOf = (color: number): [number, number, number] => [color >> 16, color >> 8 & 255, color & 255]

/**
 * Reads each frame of `movie` as the palette index of every pixel it changes,
 * through `nearest`, and the clear index everywhere else, joining a frame that
 * changes nothing onto the milliseconds of the one before.
 */
function* heldOf(movie: Movie, nearest: (color: number) => number): Generator<Held> {
  let held: Held | undefined
  for (const [frame, changed] of changesOf(movie)) {
    if (held && changed.length === 0) {
      held.delay += movie.delay
      continue
    }
    if (held) yield held
    held = { delay: movie.delay, indices: new Uint8Array(frame.length).fill(CLEAR) }
    for (const pixel of changed) held.indices[pixel] = nearest(frame[pixel]!)
  }
  if (held) yield held
}

/**
 * Ranks every color the frames of `movie` change a pixel to by how many pixels
 * take it, the most first, keeping the 255 the palette holds beside its clear
 * index.
 */
function paletteOf(movie: Movie): number[] {
  const counts = new Map<number, number>()
  for (const [frame, changed] of changesOf(movie)) {
    for (const pixel of changed) counts.set(frame[pixel]!, (counts.get(frame[pixel]!) ?? 0) + 1)
  }
  return [...counts].toSorted((a, b) => b[1] - a[1]).map(([color]) => color).slice(0, CLEAR)
}

/**
 * Encodes `movie` as a GIF89a that loops forever, one palette of the colors its
 * frames change pixels to, a color past the palette's drawn in the nearest one
 * it holds, each frame leaving every pixel it does not change clear so the
 * frame before shows through, and a frame changing nothing joined onto the
 * time of the one before.
 *
 * Returns:
 *   The GIF's bytes.
 */
export function encodeGif(movie: Movie): Uint8Array {
  const palette = paletteOf(movie)
  const colors  = palette.map(color => channelsOf(color))
  const table   = Array.from({ length: CLEAR + 1 }, (_, at) => colors[at] ?? channelsOf(0))
  const index   = new Map(palette.map((color, at) => [color, at]))
  const gif     = GIFEncoder()
  const nearest = (color: number) =>
    index.getOrInsertComputed(color, () => nearestColorIndex(colors, channelsOf(color)))

  heldOf(movie, nearest).forEach(({ delay, indices }, n) => {
    gif.writeFrame(indices, movie.width, movie.height, {
      delay            : delay,
      dispose          : 1,
      palette          : n === 0 ? table : undefined,
      transparent      : true,
      transparentIndex : CLEAR
    })
  })
  gif.finish()
  return gif.bytes()
}
