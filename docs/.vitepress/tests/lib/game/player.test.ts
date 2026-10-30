import { describe, expect, it } from 'vitest'

import type { Episode } from '../../../lib/game/episode.ts'
import * as player      from '../../../lib/game/player.ts'
import * as rooms       from '../../../lib/game/rooms.ts'
import { stand }        from '../../common/episode.ts'

/**
 * Starts an episode with Blue on `at` in `place`, stopped facing `facing`,
 * `steps` presses into the episode.
 */
function placed(
  place  : rooms.Place,
  at     : rooms.Square,
  facing : rooms.Direction,
  steps  : number = player.WANDER
): Episode {
  return Object.assign(stand(at, place, facing), { steps })
}

describe('Player', () => {
  it('plays the default episode from seed 11, choosing Squirtle at step 163', () => {
    const playing = new player.Player()
    playing.finish()
    const { chosen, flags, reached, shares, steps, total } = playing.episode

    expect([steps, total, reached.size, chosen]).toStrictEqual([163, 0.915, 61, [7, 3]])
    expect([...flags]).toStrictEqual(['appeared', 'followed', 'asked', 'starter'])
    expect(shares)
      .toStrictEqual({ milestone: 0.30000000000000004, novelty: 0.015000000000000012, starter: 0.6 })
  })

  it('plays the same episode again once reset', () => {
    const playing = new player.Player({ seed: 4 })
    const presses = () => {
      const buttons = []
      while (!playing.done) {
        playing.next()
        buttons.push(playing.button)
      }
      return buttons
    }
    const first = presses()
    playing.reset()

    expect([presses(), playing.done]).toStrictEqual([first, true])
  })

  it.each([
    [0, 0],
    [131, 131],
    [500, 163]
  ])('plays the episode again from the bedroom up to step %i, stopping at %i', (step, reached) => {
    const seeking = new player.Player()
    const fresh   = new player.Player()
    seeking.finish()
    fresh.playTo(reached)

    seeking.seek(step)

    expect([seeking.episode.steps, seeking.episode.total]).toStrictEqual([reached, fresh.episode.total])
  })
})

describe('Player under a reader', () => {
  it('presses a queued button once and a held one until let go, a new direction turning Blue first', () => {
    const playing  = new player.Player()
    playing.queued = 'left'
    playing.next()
    playing.held = 'down'
    playing.next()
    playing.next()

    expect([playing.button, playing.queued, playing.episode.at]).toStrictEqual(['down', null, [3, 7]])
  })

  it('leaves Blue walking behind Oak whatever the reader presses', () => {
    const playing = new player.Player()
    Object.assign(stand([10, 2], 'pallet', 'up', playing.episode), { steps: player.WANDER }).press('up')
    playing.queued = 'left'
    playing.held   = 'right'

    expect([playing.choose(), playing.queued]).toStrictEqual(['b', null])
  })

  it('reads its seed from the record it takes, defaulting to the one PLAYING holds', () => {
    expect([new player.Player().seed, new player.Player({ seed: 2 }).seed])
      .toStrictEqual([player.PLAYING.seed, 2])
  })
})

describe('GOALS and pickAt', () => {
  it('ends each room’s walk on its stairs, its door mat, or the north edge', () => {
    const stairs = rooms.RULES.bedroom.warps[0].at
    const mat    = rooms.RULES.house.exits[0].at

    expect(player.GOALS).toStrictEqual({ bedroom: stairs, house: mat, pallet: [10, rooms.NORTH_EDGE] })
  })

  it('ends the lab’s walk below Squirtle’s Poké Ball', () => {
    expect(rooms.ballAhead({ at: player.pickAt, place: 'lab' }, 'up')).toStrictEqual([7, 3])
  })
})

describe('autoPress', () => {
  it.each([
    ['lab', [7, 4], 'up', 'a', 'faces Squirtle’s Poké Ball'],
    ['lab', [7, 4], 'down', 'up', 'stands below it facing away'],
    ['lab', [5, 3], 'up', 'down', 'walks toward the square below it'],
    ['house', [2, 7], 'down', 'down', 'stands on the door mat'],
    ['bedroom', [3, 6], 'down', 'right', 'walks toward the stairs'],
    ['pallet', [5, 6], 'down', 'right', 'walks toward the north edge'],
    ['pallet', [0, 0], 'down', 'left', 'stands where no walk reaches the north edge, and draws a direction']
  ] as const)('presses in %s at %j facing %s %s, where Blue %s', (place, at, facing, button, _where) => {
    expect(player.autoPress(placed(place, at, facing), () => 0.5)).toBe(button)
  })

  it('presses B while Oak leads, and a random button before the wander ends', () => {
    const led = placed('pallet', [10, 2], 'up')
    led.press('up')

    expect([player.autoPress(led, () => 0), player.autoPress(placed('lab', [7, 4], 'up', 0), () => 0.99)])
      .toStrictEqual(['b', 'b'])
  })
})
