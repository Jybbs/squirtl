import { describe, expect, it } from 'vitest'

import * as sees                            from '../../../lib/front/sees.ts'
import { type Flag, eventFlags, squareKey } from '../../../lib/game/episode.ts'
import { Player, type Playing }             from '../../../lib/game/player.ts'
import { SCREEN }                           from '../../../lib/game/screen.ts'
import * as identity                        from '../../../lib/identity/identity.ts'
import SETTINGS                             from '../../../lib/rendered/settings.json' with { type: 'json' }

/**
 * The shape the settings give the environment's observation.
 */
const { frame_shape: [height, width], frame_stack: stack, grid_size: side } = SETTINGS.environment

/**
 * The presses the default episode takes to reach the starter.
 */
const last = sees.stepsOf()

/**
 * Builds an observation of the default episode whose screen is Athens Gray on
 * an odd step and Denim Deep on an even one, so each frame reads 255 or 0 by
 * the step it was captured at.
 */
function alternating(observing: sees.Observing = sees.OBSERVING): sees.Observation {
  const odd                           = screenOf(() => 'ground')
  const even                          = screenOf(() => 'deep')
  const observation: sees.Observation = new sees.Observation(
    () => observation.player.episode.steps % 2 ? odd : even,
    observing
  )
  return observation
}

/**
 * Plays the default episode until `flag` is set, returning the step that set
 * it.
 */
function firstSetting(flag: Flag): number {
  const player = new Player()
  while (!player.episode.flags.has(flag)) player.next()
  return player.episode.steps
}

/**
 * Reads the red, green, and blue of the pixel of `pixels` at `index`.
 */
function pixelAt(pixels: Uint8ClampedArray, index = 0): number[] {
  return [...pixels.subarray(index * 4, index * 4 + 3)]
}

/**
 * Reads the red, green, and blue of the color `token` names.
 */
function rgb(token: identity.Token): number[] {
  return identity.rgbOf(identity.hexOf(token))
}

/**
 * Builds a Game Boy screen, four bytes a pixel, each pixel in the color `paint`
 * names for its column and row.
 */
function screenOf(paint: (x: number, y: number) => identity.Token): Uint8ClampedArray {
  const pixels = new Uint8ClampedArray(SCREEN.width * SCREEN.height * 4)
  for (let y = 0; y < SCREEN.height; y++) {
    for (let x = 0; x < SCREEN.width; x++) pixels.set([...rgb(paint(x, y)), 255], (y * SCREEN.width + x) * 4)
  }
  return pixels
}

describe('shrink', () => {
  it.each([
    ['ground', 255],
    ['pale', 153],
    ['mid', 85],
    ['deep', 0],
    ['night', 0]
  ] as const)('turns a screen of %s to PyBoy’s gray %i', (token, gray) => {
    const frame = new Uint8Array(height! * width!)

    sees.shrink(screenOf(() => token), frame)

    expect(new Set(frame)).toStrictEqual(new Set([gray]))
  })

  it.each([
    [['ground', 'deep', 'ground', 'deep'], 128],
    [['ground', 'ground', 'ground', 'deep'], 191],
    [['pale', 'pale', 'mid', 'deep'], 98]
  ] as const)('sets each cell to the mean of its block of %j, rounding a half up', (block, mean) => {
    const frame = new Uint8Array(height! * width!)

    sees.shrink(screenOf((x, y) => block[(y % 2) * 2 + (x % 2)]!), frame)

    expect(new Set(frame)).toStrictEqual(new Set([mean]))
  })
})

describe('Observation frames', () => {
  it.each([
    [0, [0, 0, 0, 0]],
    [1, [0, 0, 0, 255]],
    [2, [0, 0, 255, 0]],
    [5, [0, 255, 0, 255]]
  ])('holds the screens to step %i newest last, padded with the first as after a reset', (step, frames) => {
    const observation = alternating()

    observation.seek(step)

    expect([3, 2, 1, 0].map(back => observation.frame(back)[0])).toStrictEqual(frames)
  })

  it('drops the oldest frame for the newest at each press', () => {
    const observation = alternating()
    observation.seek(5)

    observation.next()

    expect([observation.player.episode.steps, [3, 2, 1, 0].map(back => observation.frame(back)[0])])
      .toStrictEqual([6, [255, 0, 255, 0]])
  })

  it('stays on the episode’s last step when asked for a step past it', () => {
    const observation = alternating()

    observation.seek(last + 10)

    expect([observation.player.done, observation.player.episode.steps]).toStrictEqual([true, last])
  })
})

describe('Observation grid', () => {
  it.each([0, 40, 100, last])('marks the squares reached on Blue’s map around him at step %i', step => {
    const observation = alternating()
    const center      = Math.floor(side / 2)

    observation.seek(step)
    const { at, place, reached } = observation.player.episode
    const expected               = [...reached]
      .filter(key => key.startsWith(`${place}:`))
      .map(key => key.slice(place.length + 1).split(',').map(Number))
      .map(([x, y]) => (y! - at[1] + center) * side + x! - at[0] + center)

    expect([...observation.grid.keys()].filter(i => observation.grid[i] === 1))
      .toStrictEqual(expected.toSorted((a, b) => a - b))
    expect(observation.grid[center * side + center]).toBe(1)
  })

  it('leaves off every square farther from Blue than half the grid’s side', () => {
    const observation = alternating({ ...sees.OBSERVING, grid: 3 })

    observation.seek(last)
    const { at, place, reached } = observation.player.episode

    const around = [-1, 0, 1].flatMap(dy => [-1, 0, 1].map(dx => [at[0] + dx, at[1] + dy] as const))
    const near   = around.filter(square => reached.has(squareKey(place, square))).length
    const onMap  = [...reached].filter(key => key.startsWith(`${place}:`)).length

    expect([observation.grid.reduce((sum, each) => sum + each, 0), onMap > near]).toStrictEqual([near, true])
  })
})

describe('Observation flags', () => {
  it.each(eventFlags.map(each => [each.flag]))('sets the %s flag at the step first setting it', flag => {
    const observation = alternating()
    const first       = firstSetting(flag)
    const index       = eventFlags.findIndex(each => each.flag === flag)

    observation.seek(first - 1)
    const before = observation.flagged[index]
    observation.seek(first)

    expect([before, observation.flagged[index]]).toStrictEqual([false, true])
  })

  it('plays the episode the playing record it is given sets out', () => {
    const playing     = { seed: 3 }
    const observation = new sees.Observation(() => screenOf(() => 'ground'), sees.OBSERVING, playing)

    observation.seek(sees.stepsOf(playing))

    expect([observation.player.seed, observation.flagged[1]]).toStrictEqual([3, true])
  })
})

describe('stepsOf', () => {
  it.each([
    [undefined],
    [{ seed: 3 }]
  ])('counts the presses an episode played as %j takes to reach the starter, where it ends', playing => {
    const player = new Player(playing as Playing | undefined)
    player.finish()

    expect([sees.stepsOf(playing), player.episode.flags.has('starter')])
      .toStrictEqual([player.episode.steps, true])
  })
})

describe('bytesOf', () => {
  it.each([
    [sees.OBSERVING, { flags: 4, frames: stack * height! * width!, grid: side * side }],
    [{ ...sees.OBSERVING, frame: { height: 2, width: 3 }, grid: 5 }, { flags: 4, frames: 24, grid: 25 }]
  ])('counts a byte a pixel of each frame, a square of the grid, and a flag', (observing, bytes) => {
    expect(sees.bytesOf(observing)).toStrictEqual(bytes)
  })
})

describe('paintFrame', () => {
  it.each([
    [255, 'ground'],
    [153, 'muted'],
    [85, 'quiet'],
    [0, 'dark']
  ] as const)('draws PyBoy’s gray %i in %s, fully opaque', (gray, token) => {
    const pixels = new Uint8ClampedArray(4)

    sees.paintFrame(Uint8Array.of(gray), pixels)

    expect([...pixels]).toStrictEqual([...rgb(token), 255])
  })

  it('draws a gray halfway between two of PyBoy’s grays halfway between their colors', () => {
    const pixels   = new Uint8ClampedArray(4)
    const [lo, hi] = [rgb('muted'), rgb('ground')]

    sees.paintFrame(Uint8Array.of(204), pixels)

    expect(pixelAt(pixels)).toStrictEqual(lo.map((each, channel) => Math.round((each + hi[channel]!) / 2)))
  })
})

describe('paintGrid', () => {
  it('draws a square reached in white, one not reached in black, and Blue’s in the agent’s Denim', () => {
    const center = Math.floor(side / 2) * (side + 1)
    const grid   = new Uint8Array(side * side)
    const pixels = new Uint8ClampedArray(side * side * 4)
    grid[0]      = 1
    grid[center] = 1

    sees.paintGrid(grid, pixels)

    expect([pixelAt(pixels), pixelAt(pixels, 1), pixelAt(pixels, center), pixels[center * 4 + 3]])
      .toStrictEqual([rgb('ground'), rgb('dark'), rgb('primary'), 255])
  })
})
