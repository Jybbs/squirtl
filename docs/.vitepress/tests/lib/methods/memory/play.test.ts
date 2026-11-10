import { describe, expect, it } from 'vitest'

import { STEP }        from '../../../../lib/game/gait.ts'
import { LAST, TRACE } from '../../../../lib/methods/memory.ts'
import * as play       from '../../../../lib/methods/memory/play.ts'

/**
 * The steps that move Blue into another room, from the bedroom to the house,
 * out to Pallet Town, and into the lab.
 */
const WARPS = [104, 119, 148] as const

describe('PLAY', () => {
  it('moves Blue into the next room on each warp’s step', () => {
    expect([WARPS.map(n => [TRACE[n - 1]!.place, TRACE[n]!.place]), new Set(TRACE.map(row => row.place)).size]).toStrictEqual([
      [['bedroom', 'house'], ['house', 'pallet'], ['pallet', 'lab']], 4
    ])
  })

  it('plays a step that stays in one room over the environment’s frames, ending on its row', () => {
    expect([play.PLAY.steps[3]!.length, play.PLAY.ends[3]!.row, play.PLAY.ends[3]!.square]).toStrictEqual([STEP.frames, 3, TRACE[3]!.at])
  })

  it('walks two pixels a pass, the bytes taking the new square on the walk’s last advance', () => {
    const frames = play.PLAY.steps[2]!

    expect([frames.map(frame => frame.at[0] - 3), frames.map(frame => frame.row)]).toStrictEqual([
      [0, 0, 0.125, 0.125, 0.25, 0.25, 0.375, 0.375, 0.5, 0.5, 0.625, 0.625, 0.75, 0.75, 0.875, 0.875, 1],
      [...Array.from({ length: 16 }, () => 1), 2]
    ])
  })

  it('counts every frame of the steps on one clock', () => {
    const clocks = play.PLAY.steps.slice(1).flat().map(frame => frame.clock)

    expect(clocks).toStrictEqual(clocks.map((_, n) => n))
  })
})

describe('PLAY across a warp', () => {
  it('fades a room out through each palette with wCurMap already naming the next room', () => {
    const frames = play.PLAY.steps[WARPS[0]!]!
    const faded  = frames.filter(frame => frame.fade > 0)

    expect([new Set(faded.map(frame => frame.fade)), new Set(faded.map(frame => frame.place)), faded[0]!.map]).toStrictEqual([new Set([1, 2, 3]), new Set(['bedroom']), 0x25])
  })

  it('walks Blue down off Pallet Town’s door as he leaves the house', () => {
    const out = play.PLAY.steps[WARPS[1]]!.filter(frame => frame.place === 'pallet')

    expect([out[0]!.at, out.at(-1)!.at, out.at(-1)!.square]).toStrictEqual([[5, 5], [5, 6], [5, 6]])
  })

  it('holds the room for half a second once a warp loads it', () => {
    const frames = play.PLAY.steps[WARPS[0]!]!

    expect(frames.filter(frame => frame.place === 'house').length).toBe(30)
  })

  it('fades the last frame out and loads the bedroom again before the first step', () => {
    const restart = play.PLAY.steps[0]!

    expect([restart[0]!.place, restart.at(-1)!.place, restart.at(-1)!.clock]).toStrictEqual([TRACE[LAST]!.place, 'bedroom', 0])
  })
})

describe('REACHED', () => {
  it('shows each square first on a frame of the step that first reaches it', () => {
    const lab = play.REACHED.lab.at(-1)!

    expect(play.PLAY.steps[lab.step]!.some(frame => frame.clock === lab.seen)).toBe(true)
  })

  it('lists every square the trace reaches once', () => {
    expect(Object.values(play.REACHED).flat().length).toBe(new Set(TRACE.map(row => `${row.place}:${row.at.join()}`)).size)
  })
})
