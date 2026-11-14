import { describe, expect, it } from 'vitest'

import { type Movie, encodeGif } from '../../../lib/readme/gif.ts'
import { decodeGif }             from '../../common/gif.ts'

/**
 * Builds a movie of `frames`, each `width` pixels wide, holding 20 ms a frame.
 */
const movieOf = (width: number, frames: readonly number[][]): Movie => ({
  delay  : 20,
  frames : () => frames.map(frame => Uint32Array.from(frame)),
  height : frames[0]!.length / width,
  width  : width
})

describe('encodeGif', () => {
  it.each([
    ['a single frame', movieOf(2, [[0xff0000, 0x00ff00, 0x0000ff, 0xffffff]])],
    ['frames changing a corner', movieOf(3, [[1, 1, 1, 1, 1, 1], [1, 1, 1, 1, 1, 2], [3, 1, 1, 1, 1, 2]])]
  ])('decodes back to every frame of %s', (_, movie) => {
    const decoded = decodeGif(encodeGif(movie))

    expect(decoded.frames).toStrictEqual([...movie.frames()])
    expect([decoded.width, decoded.height]).toStrictEqual([movie.width, movie.height])
  })

  it('loops forever on one palette, every frame holding the movie’s delay', () => {
    const decoded = decodeGif(encodeGif(movieOf(1, [[1], [2], [3]])))

    expect([decoded.loops, decoded.locals]).toStrictEqual([0, 0])
    expect(decoded.delays).toStrictEqual([2, 2, 2])
  })

  it('joins a frame changing nothing onto the time of the frame before', () => {
    const decoded = decodeGif(encodeGif(movieOf(1, [[1], [2], [2], [2], [3]])))

    expect(decoded.delays).toStrictEqual([2, 6, 2])
  })

  it('draws a color past the palette’s 255 in the nearest color it holds', () => {
    const frame   = Array.from({ length: 256 }, (_, at) => at * 65_793)
    const decoded = decodeGif(encodeGif(movieOf(16, [frame, [...frame.slice(0, 255), 254 * 65_793]])))

    expect(decoded.palette).not.toContain(255 * 65_793)
    expect(decoded.frames[0]!.at(-1)).toBe(254 * 65_793)
  })
})
