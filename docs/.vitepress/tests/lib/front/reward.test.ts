import { describe, expect, it, vi } from 'vitest'

import * as reward          from '../../../lib/front/reward.ts'
import { termMark }         from '../../../lib/game/actors.ts'
import { EPISODE }          from '../../../lib/game/episode.ts'
import { RoomImages }       from '../../../lib/game/images.ts'
import { Player }           from '../../../lib/game/player.ts'
import type { ChipContent } from '../../../lib/widgets/chips.ts'

/**
 * Every step of the default episode, recorded once for every case.
 */
const TRACE = reward.traceOf()

/**
 * The bounds of an episode whose new positions pay four times what the settings
 * declare.
 */
const RICHER = { ...EPISODE, pay: { ...EPISODE.pay, novelty: 0.001 } }

/**
 * Reads what a test reads off a chip: its name, its role, its note, its value,
 * and whether it carries the game's mark.
 */
const shown = (chip: ChipContent) => [chip.name, chip.role, chip.note, chip.value, chip.mark !== '']

describe('traceOf', () => {
  it('records each step of the default episode from Blue waking to Squirtle at step 163', () => {
    const [first, last] = [TRACE[0]!, TRACE.at(-1)!]

    expect(TRACE).toHaveLength(164)
    expect([first.total, first.reached, first.flags, first.led, first.paid])
      .toStrictEqual([0, 1, [], false, []])
    expect([last.total, last.reached, last.flags])
      .toStrictEqual([0.915, 61, ['appeared', 'followed', 'asked', 'starter']])
  })

  it('marks each milestone and the starter as a jump at the return it reaches', () => {
    const jumps = TRACE.flatMap((step, at) => step.jumps.map(jump => [at, jump.term, jump.total.toFixed(5)]))

    expect(jumps).toStrictEqual([
      [131, 'milestone', '0.10975'], [156, 'milestone', '0.21450'], [156, 'milestone', '0.31450'],
      [163, 'starter', '0.91500']
    ])
  })

  it('records Oak leading Blue from the north edge until the table', () => {
    const led = TRACE.map(step => step.led)

    expect([led.indexOf(true), led.lastIndexOf(true), led.filter(Boolean).length])
      .toStrictEqual([131, 155, 25])
  })
})

describe('figuresAt', () => {
  it.each([
    [0, ['Blue wakes', 'none', null, '0.00000', false]],
    [1, ['Already reached', 'none', null, '0.00000', false]],
    [2, ['A new position', 'novelty', null, '+0.00025', true]],
    [131, ['A milestone', 'milestone', null, '+0.10025', true]],
    [132, ['Following Oak', 'none', null, '0.00000', false]],
    [156, ['Two milestones', 'milestone', null, '+0.20025', true]],
    [163, ['The starter', 'starter', null, '+0.60000', true]]
  ])('names what the press at step %i paid', (at, paid) => {
    expect(shown(reward.figuresAt(TRACE, at).paid)).toStrictEqual(paid)
  })

  it.each([
    [0, '0.00000', ['0 × 0.00025', '0 of 3', 'Not yet'], ['0.00000', '0.00000', '0.00000']],
    [131, '0.10975', ['39 × 0.00025', '1 of 3', 'Not yet'], ['0.00975', '0.10000', '0.00000']],
    [163, '0.91500', ['60 × 0.00025', '3 of 3', 'Squirtle'], ['0.01500', '0.30000', '0.60000']]
  ])('sets the return, the step, and each term so far at step %i', (at, total, notes, values) => {
    const figures = reward.figuresAt(TRACE, at)

    expect([figures.total, figures.step]).toStrictEqual([total, `Step ${at} of 163`])
    expect(figures.terms.map(term => [term.name, term.note, term.value])).toStrictEqual([
      ['New positions', notes[0], values[0]],
      ['Milestones', notes[1], values[1]],
      ['The starter', notes[2], values[2]]
    ])
  })

  it('reads what a new position pays from the settings it is given', () => {
    expect(reward.figuresAt(TRACE, 0, RICHER).terms[0]!.note).toBe('0 × 0.00100')
  })

  it('marks each term with the game’s mark for it and sets every name as published prose', () => {
    const figures = reward.figuresAt(TRACE, 156)

    expect(figures.terms.map(term => term.mark)).toStrictEqual(reward.terms.map(term => termMark(term)))
    for (const chip of [figures.paid, ...figures.terms]) expect(chip.name).toBePublishedProse()
  })
})

describe('terms and marks', () => {
  it('orders the terms by what one press of each pays, the least first, each beside its mark', () => {
    expect(reward.terms).toStrictEqual(['novelty', 'milestone', 'starter'])
    expect(Object.entries(reward.marks)).toStrictEqual(reward.terms.map(term => [term, termMark(term)]))
  })
})

describe('keyTerms', () => {
  it.each([
    [EPISODE, ['+0.00025', '+0.10000', '+0.60000', '0.00000']],
    [RICHER, ['+0.00100', '+0.10000', '+0.60000', '0.00000']]
  ])('sets each term in its hue beside what a press of it pays, then nothing new', (settings, values) => {
    expect(reward.keyTerms(settings).map(chip => shown(chip))).toStrictEqual([
      ['New positions', 'novelty', null, values[0], true],
      ['Milestones', 'milestone', null, values[1], true],
      ['The starter', 'starter', null, values[2], true],
      ['Already reached', 'none', null, values[3], false]
    ])
  })
})

describe('describeStep', () => {
  it.each([
    [0, 'Step 0 of 163, the return 0.00000'],
    [12, 'Step 12 of 163, the return 0.00050'],
    [163, 'Step 163 of 163, the return 0.91500']
  ])('describes step %i for a screen reader', (at, words) => {
    expect(reward.describeStep(TRACE, at)).toBe(words)
  })
})

describe('playingOf', () => {
  it('beats a press each beat, and more slowly while Oak leads Blue', () => {
    const player  = new Player()
    const playing = reward.playingOf(player, () => {})
    const beat    = playing.beat as () => number
    const before  = beat()
    player.seek(140)

    expect([before, beat(), playing.rest]).toStrictEqual([120, 170, 3600])
  })

  it('presses on each tick, plays again from the bedroom on restart, and plays to the end on finish', () => {
    const player  = new Player()
    const show    = vi.fn<(span: number) => void>()
    const playing = reward.playingOf(player, show, { ...reward.TEMPO, glide: 80 })

    playing.tick()
    const ticked = player.episode.steps
    playing.finish()
    const done = [player.episode.steps, playing.done()]
    playing.restart!()

    expect([ticked, done, player.episode.steps, playing.done()]).toStrictEqual([1, [163, true], 0, false])
    expect(show.mock.calls).toStrictEqual([[80], [0], [0]])
  })
})

describe('showingOf', () => {
  it('sets the screen on the episode the player presses, drawing the rooms through the images given', () => {
    const images  = new RoomImages(source => ({ source }) as never)
    const showing = reward.showingOf(images, { seed: 4 })

    expect([showing.images, showing.screen.episode, showing.player.seed])
      .toStrictEqual([images, showing.player.episode, 4])
    expect(showing.trace).toStrictEqual(reward.traceOf({ seed: 4 }))
  })

  it('loads the rooms through the page’s own images unless given some', () => {
    expect(reward.showingOf().images).toBeInstanceOf(RoomImages)
  })
})
