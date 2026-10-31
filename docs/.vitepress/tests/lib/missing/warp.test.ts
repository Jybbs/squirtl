import { describe, expect, it } from 'vitest'

import * as warp from '../../../lib/missing/warp.ts'

/**
 * Groups `frames` into runs of one facing, palette, and height, each beside the
 * frames it lasts.
 */
const runsOf = (frames: readonly warp.WarpFrame[]): (number | string)[][] =>
  frames.reduce<(number | string)[][]>((runs, { facing, palette, y }) => {
    const last = runs.at(-1)
    const same = last?.[0] === facing && last[1] === palette && last[2] === y
    if (same) last[3] = Number(last[3]) + 1
    else runs.push([facing, palette, y, 1])
    return runs
  }, [])

/**
 * Reports whether `frame` stands Blue on his square behind the white screen.
 */
const onWhite = (frame: warp.WarpFrame): boolean => frame.palette === '0000' && frame.y === warp.Y.stand

describe('warpFrames', () => {
  it('spins Blue in place slowing from 15 frames a facing to 1, then up off the screen to white', () => {
    const spins = [15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
      .map((wait, at) => [['down', 'left', 'up', 'right'][at % 4]!, '3210', 60, wait])

    expect(runsOf(warp.warpFrames({ arrive: false }))).toStrictEqual([
      ...spins,
      ['down', '3210', 44, 3], ['left', '3210', 28, 3], ['up', '3210', 12, 3], ['right', '3210', -4, 3],
      ['down', '3210', -20, 10], ['down', '2100', -20, 8], ['down', '1000', -20, 8], ['down', '0000', -20, 8]
    ])
  })

  it('fades in from white, spins Blue down onto his square, and slows his spin to a stop facing down', () => {
    expect(runsOf(warp.warpFrames({ out: false }))).toStrictEqual([
      ['down', '0000', -20, 3], ['down', '1000', -20, 8], ['down', '2100', -20, 8], ['down', '3210', -20, 8],
      ['down', '3210', -4, 3], ['left', '3210', 12, 3], ['up', '3210', 28, 3], ['right', '3210', 44, 3],
      ['left', '3210', 60, 1], ['up', '3210', 60, 2], ['right', '3210', 60, 3], ['down', '3210', 60, 4],
      ['left', '3210', 60, 5], ['up', '3210', 60, 6], ['right', '3210', 60, 7], ['down', '3210', 60, 1]
    ])
  })

  it('stands Blue still before he leaves and holds the screen white once he is back on his square', () => {
    const frames = warp.warpFrames({ stand: 5, white: 4 })
    const white  = frames.filter(frame => onWhite(frame))

    expect([frames.length - warp.warpFrames().length, frames.slice(0, 5), white.length]).toStrictEqual([
      9, Array.from({ length: 5 }, () => warp.warpLoop[0]), 4
    ])
  })
})

describe('warpLoop', () => {
  it('opens and closes on Blue standing on his square facing down in the map’s own shades', () => {
    const standing = { facing: 'down', palette: '3210', y: warp.Y.stand }

    expect([warp.warpLoop[0], warp.warpLoop.at(-1), warp.warpLoop.length])
      .toStrictEqual([standing, standing, 414])
  })
})
