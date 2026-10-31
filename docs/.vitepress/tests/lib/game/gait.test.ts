import { describe, expect, it } from 'vitest'

import * as gait       from '../../../lib/game/gait.ts'
import type { Button } from '../../../lib/game/rooms.ts'

/**
 * Lists the frames of a step's stances, counted from 1, on which Blue shows
 * `stance`.
 */
const framesIn = (stances: readonly gait.Stance[], stance: gait.Stance): number[] =>
  [...stances.entries()].filter(([, each]) => each === stance).map(([frame]) => frame + 1)

/**
 * Makes an array of `count` frames' stances, each standing until a step writes
 * it.
 */
const framesOf = (count: number): gait.Stance[] =>
  Array.from({ length: count }, (): gait.Stance => 'standing')

/**
 * Lists the frames of a step's stances on which Blue walks on the plain frame
 * and on the mirrored one.
 */
const strides = (stances: readonly gait.Stance[]): number[][] =>
  [framesIn(stances, 'walking'), framesIn(stances, 'mirrored')]

/**
 * Runs `gait` through the step `n` with `held` pressed, a fresh array of the
 * step's frames holding its stances.
 */
function stepped(
  walker  : gait.Gait,
  n       : number,
  held    : Button | null,
  blocked : boolean = false,
  turn    : boolean = false
): gait.Stance[] {
  return walker.step(n, held, blocked, turn, framesOf(gait.STEP.frames))
}

describe('STEP', () => {
  it('runs each step over the frames the settings tick, holding its button for the emulator’s hold', () => {
    expect(gait.STEP).toStrictEqual({ frames: 17, hold: 2 })
  })
})

describe('Gait.step', () => {
  it('walks the first step of a walk on the plain walking frame, every fourth tick moving it on', () => {
    expect(framesIn(stepped(new gait.Gait('down'), 0, 'down'), 'walking'))
      .toStrictEqual([8, 9, 10, 11, 12, 13, 14, 15])
  })

  it('walks the next step on the other foot and the one after on the plain frame again', () => {
    const walker = new gait.Gait('down')
    const steps  = [0, 1, 2].map(n => stepped(walker, n, 'down'))

    expect(steps.map(stances => strides(stances))).toStrictEqual([
      [[8, 9, 10, 11, 12, 13, 14, 15], []],
      [[], [7, 8, 9, 10, 11, 12, 13, 14]],
      [[6, 7, 8, 9, 10, 11, 12, 13], []]
    ])
  })

  it('faces Blue the way he presses and moves him only where the square ahead is open', () => {
    const blocked = new gait.Gait('down')
    const walked  = new gait.Gait('down')

    const still = stepped(blocked, 0, 'left', true)
    const moved = stepped(walked, 0, 'left')

    expect([blocked.facing, still.includes('walking'), walked.facing, moved.includes('walking')])
      .toStrictEqual(['left', false, 'left', true])
  })

  it('turns Blue in place with no tick through a press that only turns him', () => {
    const walker = new gait.Gait('down')
    const turned = stepped(walker, 0, 'left', true, true)

    expect([walker.facing, turned.every(stance => stance === 'standing')]).toStrictEqual(['left', true])
  })
})

describe('Gait.step at rest', () => {
  it.each([
    ['A', 'a'],
    ['no button', null]
  ] as const)('stands Blue still through a press of %s with no walk under way', (_, held) => {
    const walker = new gait.Gait('up')

    expect([stepped(walker, 0, held).every(stance => stance === 'standing'), walker.facing])
      .toStrictEqual([true, 'up'])
  })

  it('zeroes the counters once a pass after the walk holds no direction', () => {
    const walker = new gait.Gait('down')
    stepped(walker, 0, 'down')
    stepped(walker, 1, 'b')

    expect(framesIn(stepped(walker, 0, 'down'), 'walking')).toStrictEqual([8, 9, 10, 11, 12, 13, 14, 15])
  })
})

describe('Gait.reset', () => {
  it('stands Blue still facing the way given, his counters cleared mid-walk', () => {
    const walker = new gait.Gait('down')
    walker.step(0, 'down', false, false, framesOf(9), { frames: 9, hold: 2 })

    walker.reset('up')

    expect([walker.facing, walker.stance, framesIn(stepped(walker, 0, 'up'), 'walking')])
      .toStrictEqual(['up', 'standing', [8, 9, 10, 11, 12, 13, 14, 15]])
  })
})

describe('stanceAt', () => {
  it.each([
    ['the first frame’s at the step’s start', 0, 'standing'],
    ['the frame a share of the way reaches', 0.5, 'walking'],
    ['the last frame’s once the step ends', 1, 'mirrored']
  ] as const)('reads %s', (_, t, stance) => {
    expect(gait.stanceAt(['standing', 'walking', 'mirrored'], t)).toBe(stance)
  })
})

describe('stancesOf', () => {
  it('runs a press each step of a walk takes, a press that only turns Blue standing him still', () => {
    const presses = gait.stancesOf([
      { at: [5, 6], facing: 'down' },
      { at: [5, 6], facing: 'up' },
      { at: [5, 5], facing: 'up' },
      { at: [5, 4], facing: 'up' }
    ])

    expect(presses.map(stances => strides(stances))).toStrictEqual([
      [[], []],
      [[9, 10, 11, 12, 13, 14, 15, 16], []],
      [[], [8, 9, 10, 11, 12, 13, 14, 15]]
    ])
  })

  it('runs no press for a walk of one place', () => {
    expect(gait.stancesOf([{ at: [5, 6], facing: 'down' }])).toStrictEqual([])
  })
})
