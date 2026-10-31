import { describe, expect, it, vi } from 'vitest'

import { walksOf }                                from '../../../../lib/front/learning.ts'
import { fillsOf }                                from '../../../../lib/front/learning/tints.ts'
import { type Town, battlePhases, circleTilesOf } from '../../../../lib/front/learning/transition.ts'
import { PLAY, Walks }                            from '../../../../lib/front/learning/walks.ts'
import { frameFor }                               from '../../../../lib/game/actors.ts'
import { stanceAt }                               from '../../../../lib/game/gait.ts'
import { runsFor }                                from '../../../../lib/game/screen.ts'
import { spriteShades }                           from '../../../../lib/identity/identity.ts'
import { Recorder }                               from '../../../common/canvas.ts'

/**
 * The walks the front page reads, read once for every case.
 */
const moments = walksOf()

/**
 * The ink a case's town closes the circle in, which no sprite draws in.
 */
const INK = '#010203'

/**
 * A town whose view in each palette is a stand-in naming that palette.
 */
const TOWN: Town = {
  ink      : INK,
  tiles    : circleTilesOf(),
  palettes : new Map(['0000', '1000', '2100', '3210', '3321', '3332', '3333']
    .map(palette => [palette, { palette } as unknown as ImageData]))
}

/**
 * The runs of Blue standing facing down, the frame a stack of Blues at the door
 * shows.
 */
const blue = runsFor(frameFor('player', 'down').grid)

/**
 * Draws `walks` onto a fresh recorder and returns it.
 */
function drawn(walks: Walks, town: Town = TOWN): Recorder {
  const screen = new Recorder()
  walks.draw(screen, town)
  return screen
}

describe('Walks setting a press', () => {
  it.each([0, 10, 100, 204])('places every Blue where his walk stands after %i presses', press => {
    const walks = new Walks(moments)

    walks.set(press)

    expect(walks.blues.map(walker => [walker.x, walker.y]))
      .toStrictEqual(moments.map(moment => [...moment.steps[Math.min(press, moment.presses)]!.at]))
  })

  it('leaves a Blue whose walk has ended facing Oak under the shock bubble as the clock plays on', () => {
    const walks = new Walks(moments)
    walks.set(moments.at(-1)!.presses)

    walks.set(moments.at(-1)!.presses + 1, PLAY.press)

    const [six, , , fifty] = walks.blues

    expect([fifty!.facing, fifty!.bubble, six!.bubble]).toStrictEqual(['down', 'shock', 'question'])
  })

  it.each([[203, false], [204, true]])('brings Oak in at %i presses once every walk ends', (press, oak) => {
    const walks = new Walks(moments)

    walks.set(press)

    expect(walks.oak).toBe(oak)
  })

  it('turns a Blue on his square in the stance his gait reaches through the press that only turns him', () => {
    const fifty = moments.at(-1)!
    const turn  = fifty.steps.slice(1).findIndex((step, n) => step.facing !== fifty.steps[n]!.facing) + 1
    const walks = new Walks([fifty])
    walks.set(turn - 1)

    walks.set(turn, PLAY.press)
    walks.advance(PLAY.press / 2)
    const walker = walks.blues[0]!

    expect([walker.x, walker.y, walker.facing, walker.stance]).toStrictEqual([
      ...fifty.steps[turn - 1]!.at, fifty.steps[turn]!.facing, stanceAt(fifty.stances[turn - 1]!, 0.5)
    ])
  })
})

describe('Walks drawing', () => {
  it('draws nothing until the town holds its view', () => {
    const screen = drawn(new Walks(moments), { ink: INK, palettes: new Map(), tiles: [] })

    expect([screen.views, screen.marks]).toStrictEqual([[], []])
  })

  it('draws the Blues standing on one square once, crossfading through their walks’ hues', () => {
    const walks  = new Walks(moments)
    const before = drawn(walks)

    const moving = walks.advance(PLAY.blend / 2)
    const after  = drawn(walks)

    expect([before.marks.length, after.marks.length, walks.grouped, moving])
      .toStrictEqual([blue.length, blue.length, true, true])
    expect(before.marks.map(mark => mark.fill)).toDrawFrom(fillsOf('amethyst'))
    expect(after.marks.map(mark => mark.fill)).toDrawFrom(fillsOf('heath'))
  })

  it('draws a picked-out Blue at full strength in his own hue and dims every other', () => {
    const walks = new Walks(moments)
    walks.set(100)
    walks.focus = 1

    const screen = drawn(walks)
    const full   = screen.marks.filter(mark => mark.alpha === 1)

    expect(screen.marks).toContainEqual(expect.objectContaining({ alpha: PLAY.dim }))
    expect(full.map(mark => mark.fill)).toDrawFrom(fillsOf('fern'))
    expect(walks.grouped).toBe(false)
  })
})

describe('Walks drawing Oak and settling', () => {
  it('draws Oak in the game’s own shades, facing up at the Blues on the north edge', () => {
    const walks = new Walks(moments)
    walks.set(walks.longest)
    walks.oak   = false
    const blues = drawn(walks).marks.length

    walks.oak = true
    const oak = drawn(walks).marks.slice(0, -blues)

    expect(new Set(walks.blues.map(walker => walker.y))).toStrictEqual(new Set([1]))
    expect(oak).toHaveLength(runsFor(frameFor('oak', 'up').grid).length)
    expect(oak.map(mark => mark.fill)).toDrawFrom(spriteShades)
  })

  it('stops moving once every glide has ended and no Blues stand on one square', () => {
    const walks = new Walks([moments.at(-1)!])
    walks.set(1, PLAY.press)

    const gliding = walks.advance(PLAY.press)
    drawn(walks)
    const settled = walks.advance(16)

    expect([gliding, settled]).toStrictEqual([true, false])
  })
})

describe('Walks encountering a wild battle', () => {
  it('flashes, closes the circle, holds black, and fades back in, calling covered once in the black', () => {
    const walks   = new Walks(moments)
    const covered = vi.fn<() => void>()
    walks.encounter(covered)
    const { black, circle, end, flash, flashStep } = battlePhases
    const times                                    = [3 * flashStep + 1, flash + 260, circle + 1, black + 150, end + 1]
    let elapsed                                    = 0

    const phases = times.map(t => {
      walks.advance(t - elapsed)
      elapsed = t
      return [walks.palette, walks.tiles, walks.sprites, covered.mock.calls.length, walks.closing]
    })

    expect(phases).toStrictEqual([
      ['3332', -1, true, 0, true],
      ['3210', 5, true, 0, true],
      ['3333', -1, false, 1, true],
      ['3332', -1, true, 1, true],
      ['3210', -1, true, 1, false]
    ])
  })

  it('draws the tiles the circle has closed in the town’s darkest shade, and no sprite in the black', () => {
    const walks = new Walks(moments)
    walks.encounter(() => {})
    walks.advance(battlePhases.flash + 260)
    const circle = drawn(walks).marks.filter(mark => mark.fill === INK).length

    walks.advance(battlePhases.circle - battlePhases.flash)
    const black = drawn(walks)

    expect(circle).toBeGreaterThan(0)
    expect([black.marks, black.views]).toStrictEqual([[], [TOWN.palettes.get('3333')]])
  })

  it('returns to the town’s own palette at once when calmed', () => {
    const walks = new Walks(moments)
    walks.encounter(() => {})
    walks.advance(battlePhases.circle + 1)

    walks.calm()

    expect([walks.palette, walks.tiles, walks.sprites, walks.closing])
      .toStrictEqual(['3210', -1, true, false])
  })
})
