import { describe, expect, it } from 'vitest'

import * as city    from '../../../lib/missing/city.ts'
import { Recorder } from '../../common/canvas.ts'

/**
 * A room two blocks wide and one block tall inside a pad of one square, whose
 * image is 96 pixels across and 64 down.
 */
const ROOM = { h: 2, pad: 1, w: 4 }

/**
 * Makes the pixels of `ROOM`'s image with a mark of `shade` at the top left of
 * its first block and of `other` at the top left of its second.
 */
function imageOf(shade: number, other: number): Pick<ImageData, 'data' | 'width'> {
  const width = 96
  const data  = new Uint8ClampedArray(width * 64 * 4)
  data[(16 * width + 16) * 4] = shade
  data[(16 * width + 48) * 4] = other
  return { data, width }
}

describe('blocksOf', () => {
  it('keeps each block of the map inside the pad once, in reading order', () => {
    expect(city.blocksOf(imageOf(1, 2), ROOM)).toStrictEqual([[16, 16], [48, 16]])
  })

  it('keeps a block whose pixels match an earlier block’s only once', () => {
    expect(city.blocksOf(imageOf(1, 1), ROOM)).toStrictEqual([[16, 16]])
  })

  it('reads Pallet Town’s map unless given another room', () => {
    const data = new Uint8ClampedArray(512 * 480 * 4)

    expect(city.blocksOf({ data, width: 512 })).toStrictEqual([[96, 96]])
  })
})

describe('cityOf', () => {
  it('reads the address’s bytes as block numbers, one to each place, cycling through the address', () => {
    const places = city.cityOf('ab', 3)

    expect([places.length, places.slice(0, 4)]).toStrictEqual([25, [1, 2, 1, 2]])
  })

  it('draws a different city for a different address', () => {
    const swapped = city.cityOf('squirtl.fyi/methods/agnet/', 7)

    expect(swapped).not.toStrictEqual(city.cityOf('squirtl.fyi/methods/agent/', 7))
  })
})

describe('paintCity', () => {
  it('cuts each place’s block from the room’s image onto the screen’s grid of blocks', () => {
    const recorder = new Recorder()
    const image    = {} as CanvasImageSource

    city.paintCity(recorder, image, 'ab', [[0, 0], [32, 0], [64, 0]], { columns: 2, rows: 2, top: 0 })

    expect(recorder.images).toStrictEqual([
      [image, 32, 0, 32, 32, 0, 0, 32, 32], [image, 64, 0, 32, 32, 32, 0, 32, 32],
      [image, 32, 0, 32, 32, 0, 32, 32, 32], [image, 64, 0, 32, 32, 32, 32, 32, 32]
    ])
  })
})
