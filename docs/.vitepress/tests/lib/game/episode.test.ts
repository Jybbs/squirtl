import { describe, expect, it } from 'vitest'

import EVENTS       from '../../../lib/rendered/events.json' with { type: 'json' }
import SETTINGS     from '../../../lib/rendered/settings.json' with { type: 'json' }
import * as episode from '../../../lib/game/episode.ts'
import * as rooms   from '../../../lib/game/rooms.ts'
import { stand }    from '../../common/episode.ts'

/**
 * What each term of the reward pays, as the settings declare it.
 */
const PAY = SETTINGS.reward

/**
 * The payment of a step setting a milestone's flag for the first time.
 */
const MILESTONE: episode.Paid = { pay: PAY.milestone, term: 'milestone' }

/**
 * The payment of a step onto a square not reached before.
 */
const NEW: episode.Paid = { pay: PAY.novelty, term: 'novelty' }

/**
 * Starts an episode with Blue on `at` in `place`, stopped facing `facing`, that
 * square counted as reached.
 */
function placed(place: rooms.Place, at: rooms.Square, facing: rooms.Direction): episode.Episode {
  const game = stand(at, place, facing)
  game.reached.add(game.key())
  return game
}

/**
 * Starts an episode with Oak just appeared at the north edge of Pallet Town.
 */
function stopped(): episode.Episode {
  const game = placed('pallet', [10, 2], 'up')
  game.press('up')
  return game
}

describe('Episode', () => {
  it('wakes Blue on 3, 6 of his bedroom facing down, that square the one reached', () => {
    const game = new episode.Episode()

    expect([game.place, game.at, game.facing, game.steps, game.total, game.done, [...game.reached]])
      .toStrictEqual(['bedroom', [3, 6], 'down', 0, 0, false, ['bedroom:3,6']])
  })
})

describe('Episode.press', () => {
  it.each([
    ['left', 'left', 'left'],
    ['down', 'down', 'down'],
    ['up', 'up', 'up'],
    ['a', 'down', null],
    ['b', 'down', null]
  ] as const)('presses %s first, leaving Blue in place facing %s and stopped in %s', (button, ...stands) => {
    const game = new episode.Episode()

    expect([game.press(button), game.at, game.steps]).toStrictEqual([[], [3, 6], 1])
    expect([game.facing, game.lastStop]).toStrictEqual(stands)
  })

  it('turns Blue in place on a new direction, and steps him on a second press of it', () => {
    const game = new episode.Episode()

    expect([game.press('left'), game.at, game.press('left'), game.at, game.steps]).toStrictEqual([
      [], [3, 6], [NEW], [2, 6], 2
    ])
  })

  it('pays nothing for a step back onto a square already reached', () => {
    const game = new episode.Episode()
    game.press('left')
    game.press('left')
    game.press('right')

    expect(game.press('right')).toStrictEqual([])
    expect([game.at, game.shares.novelty]).toStrictEqual([[3, 6], PAY.novelty])
  })

  it.each([
    ['bedroom', [7, 2], 'up', 'house', [7, 1], 'up'],
    ['house', [7, 2], 'up', 'bedroom', [7, 1], 'up'],
    ['house', [2, 7], 'down', 'pallet', [5, 6], 'down'],
    ['pallet', [5, 6], 'up', 'house', [2, 7], 'up']
  ] as const)('warps Blue from %s at %j by %s to %s at %j facing %s', (place, at, button, ...stands) => {
    const game = placed(place, at, button)

    expect(game.press(button)).toStrictEqual([NEW])
    expect([game.place, game.at, game.facing]).toStrictEqual(stands)
  })
})

describe('Episode behind Oak', () => {
  it('has Oak stop Blue on the north edge, paying a milestone and starting his walk to the lab', () => {
    const game = placed('pallet', [10, 2], 'up')

    expect([game.press('up'), [...game.flags]]).toStrictEqual([[NEW, MILESTONE], ['appeared']])
    expect(game.leader).toStrictEqual({ at: [10, 2], facing: 'down', place: 'pallet' })
    expect(game.script).toHaveLength(rooms.OAK_LEADS.length + rooms.LAB_ENTRY.length)
  })

  it('lets Blue onto the north edge without a stop once Oak has appeared', () => {
    const game = placed('pallet', [10, 2], 'up')
    game.flags.add('appeared')

    expect(game.press('up')).toStrictEqual([NEW])
    expect(game.script).toStrictEqual([])
  })

  it('walks Blue behind Oak whatever he presses, into the lab and up to the table', () => {
    const game = stopped()
    const walk = game.script.length
    const paid = Array.from({ length: walk }, (_, n) => game.press(rooms.BUTTONS[n % rooms.BUTTONS.length]!))

    expect(paid[0]).toStrictEqual([])
    expect([paid.at(-1), [...game.flags]])
      .toStrictEqual([[NEW, MILESTONE, MILESTONE], ['appeared', 'followed', 'asked']])
    expect([game.place, game.at, game.facing, game.leader, game.steps])
      .toStrictEqual(['lab', [5, 3], 'up', null, walk + 1])
    expect(game.shares.milestone).toBeCloseTo(3 * PAY.milestone, 12)
  })

  it('pays each milestone once, however often the game reaches it', () => {
    const game = stopped()
    game.flags.add('followed')
    const paid = Array.from({ length: game.script.length }, () => game.press('b'))

    expect([paid.at(-1), [...game.flags]])
      .toStrictEqual([[NEW, MILESTONE], ['appeared', 'followed', 'asked']])
  })

  it('turns Blue up and has Oak lead from inside the lab as the walk enters it', () => {
    const game = stopped()
    for (let n = 0; n <= rooms.OAK_LEADS.length; n++) game.press('b')

    expect([game.place, game.at, game.facing]).toStrictEqual(['lab', [5, 11], 'up'])
    expect(game.leader).toStrictEqual({ at: [5, 10], facing: 'up', place: 'lab' })
  })
})

describe('Episode at its end', () => {
  it('chooses the starter with A facing Squirtle’s Poké Ball, which ends the episode', () => {
    const game = placed('lab', [7, 4], 'up')

    expect(game.press('a')).toStrictEqual([{ pay: PAY.starter, term: 'starter' }])
    expect([game.done, game.terminated, game.chosen, game.flags.has('starter')])
      .toStrictEqual([true, true, [7, 3], true])
    expect(game.press('left')).toStrictEqual([])
    expect(game.steps).toBe(1)
  })

  it('ends at the limit its settings give it, a press past it counting nothing', () => {
    const game = new episode.Episode({ ...episode.EPISODE, limit: 2 })
    game.press('b')
    game.press('left')

    expect([game.done, game.press('left'), game.steps]).toStrictEqual([true, [], 2])
  })

  it('reads its limit and its payments from the settings by default', () => {
    expect(episode.EPISODE)
      .toStrictEqual({ limit: SETTINGS.environment.max_episode_steps, pay: SETTINGS.reward })
  })

  it('starts again from the bedroom with every count and flag cleared', () => {
    const game = stopped()
    game.reset()

    expect(game).toStrictEqual(new episode.Episode())
  })
})

describe('eventFlags and milestones', () => {
  it('names each event flag in the order the package declares the events, each with the term it pays', () => {
    expect(episode.eventFlags.map(each => [each.flag, each.term])).toStrictEqual([
      ['followed', 'milestone'],
      ['starter', 'starter'],
      ['appeared', 'milestone'],
      ['asked', 'milestone']
    ])
    expect(episode.eventFlags.map(each => each.term)).toStrictEqual(EVENTS.map(event => event.term))
  })

  it('reads the milestones as the flags whose events pay one', () => {
    expect(episode.milestones).toStrictEqual(['followed', 'appeared', 'asked'])
  })
})

describe('squareKey', () => {
  it('writes a square as its room, its column, and its row', () => {
    expect(episode.squareKey('lab', [7, 4])).toBe('lab:7,4')
  })
})
