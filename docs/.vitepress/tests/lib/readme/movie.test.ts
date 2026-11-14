import { describe, expect, it } from 'vitest'

import { WALKING, walksOf }   from '../../../lib/front/learning.ts'
import { VIEW, battlePhases } from '../../../lib/front/learning/transition.ts'
import { PLAY }               from '../../../lib/front/learning/walks.ts'
import * as movie             from '../../../lib/readme/movie.ts'

/**
 * One walk, the one after 50 episodes, which arrives in a handful of presses.
 */
const MOMENTS = walksOf({ ...WALKING, moments: [50] })

/**
 * The README's preview at a frame each 200 ms with a rest of two frames, so a
 * case plays a few dozen frames rather than the hundreds the README carries.
 */
const QUICK: movie.Preview = { ...movie.PREVIEW, frame: 200, rest: 400 }

describe('previewMovie', () => {
  it.each([
    ['dark', 0x0d_11_17],
    ['light', 0xff_ff_ff]
  ] as const)('draws the %s preview beside its column on GitHub’s ground', (scheme, ground) => {
    const played = movie.previewMovie(import.meta.url, MOMENTS, QUICK, scheme)
    const width  = VIEW.width * QUICK.scale + QUICK.tally.width
    const [first] = played.frames()

    expect([played.width, played.height, played.delay]).toStrictEqual([width, VIEW.height * QUICK.scale, 200])
    expect(first![width - 1]).toBe(ground)
  })

  it('plays a frame each `frame` ms until the encounter that starts the loop again has ended', () => {
    const played = movie.previewMovie(import.meta.url, MOMENTS, QUICK, 'light')
    const span   = MOMENTS[0]!.presses * PLAY.press + QUICK.rest + battlePhases.end

    expect([...played.frames()]).toHaveLength(Math.ceil(span / QUICK.frame))
  })

  it('draws the town at `scale` times its pixels, each pixel of the town a square of one color', () => {
    const played    = movie.previewMovie(import.meta.url, MOMENTS, QUICK, 'light')
    const [first]   = played.frames()
    const { scale } = QUICK
    const rows      = Array.from({ length: VIEW.height }, (_, y) =>
      first!.subarray(scale * y * played.width, scale * y * played.width + VIEW.width * scale))

    expect(new Set(rows.flatMap(row => [...row])).size).toBeGreaterThan(4)
    expect(rows.every((row, y) => row.every((color, x) =>
      color === first![(scale * y + scale - 1) * played.width + x - x % scale]))).toBe(true)
  })
})
