import { describe, expect, it } from 'vitest'

import { seeded } from '../../../lib/game/random.ts'
import * as rooms from '../../../lib/game/rooms.ts'
import * as town  from '../../../lib/game/town.ts'
import SETTINGS   from '../../../lib/rendered/settings.json' with { type: 'json' }

/**
 * The index of each button in the order a learner's table holds them.
 */
const PRESS = { a: 4, down: 1, left: 2, right: 3, up: 0 }

/**
 * The state of the square outside the door of Blue's house.
 */
const DOOR = town.stateOf([5, 6])

/**
 * What a step onto a new square on the north edge pays.
 */
const EDGE = SETTINGS.reward.novelty + SETTINGS.reward.milestone

/**
 * Presses Right until Blue stands in column 10 and Up from there.
 */
function eastThenNorth(state: number): number {
  return town.squareOf(state)[0] < 10 ? PRESS.right : PRESS.up
}

describe('townStep', () => {
  it.each([
    ['refuses the door of Blue’s house', [5, 6], PRESS.up, [5, 6], 0, false],
    ['pays a new square west of the door', [5, 6], PRESS.left, [4, 6], SETTINGS.reward.novelty, false],
    ['leaves Blue in place for A', [5, 6], PRESS.a, [5, 6], 0, false],
    ['leaves Blue in place for a button past B', [5, 6], 9, [5, 6], 0, false],
    ['refuses the lab’s door', [12, 12], PRESS.up, [12, 12], 0, false],
    ['pays the milestone on the north edge', [10, 2], PRESS.up, [10, 1], EDGE, true]
  ] as const)('%s', (_, at, action, to, reward, done) => {
    const seen = new Uint8Array(town.townStates)

    expect(town.townStep(action, seen, town.stateOf(at)))
      .toStrictEqual({ done, next: town.stateOf(to), reward })
  })

  it('pays nothing for a square already seen, nor for a new one where the learner pays no novelty', () => {
    const seen = new Uint8Array(town.townStates)
    town.townStep(PRESS.left, seen, DOOR)

    const again = town.townStep(PRESS.left, seen, DOOR)
    const free  = town.townStep(PRESS.right, seen, DOOR, 0)

    expect([again.reward, free.reward]).toStrictEqual([0, 0])
    expect([seen[town.stateOf([4, 6])], seen[town.stateOf([6, 6])]]).toStrictEqual([1, 1])
  })
})

describe('townStart', () => {
  it('starts every walk where the house’s door mats put Blue, the state of the door', () => {
    expect([town.townStart, town.townDoor]).toStrictEqual([rooms.RULES.house.exits[0].arrive, DOOR])
  })
})

describe('playTown', () => {
  it('walks a random walk from seed 5 for its whole budget, short of the north edge', () => {
    const walk = town.playTown(500, seeded(5), (state, random) => Math.floor(random() * 6))

    expect([walk.reached, walk.steps, walk.trail.length, walk.facings.length, walk.trail.at(-1)])
      .toStrictEqual([false, 500, 501, 501, town.stateOf([1, 11])])
  })

  it('turns Blue before each change of direction, reaching the north edge in twelve presses', () => {
    const walk = town.playTown(100, seeded(1), eastThenNorth)

    expect([walk.reached, walk.steps, walk.trail[0], walk.trail[1], walk.trail.at(-1)])
      .toStrictEqual([true, 12, town.townDoor, town.townDoor, town.stateOf([10, 1])])
    expect(walk.facings.join(' ')).toBe(`${town.TOWN_FACING}${' right'.repeat(6)}${' up'.repeat(6)}`)
  })

  it('leaves Blue facing the way he faced for a press of A or B', () => {
    const walk = town.playTown(2, seeded(1), () => PRESS.a)

    expect([walk.trail, walk.facings]).toStrictEqual([
      [town.townDoor, town.townDoor, town.townDoor], [town.TOWN_FACING, town.TOWN_FACING, town.TOWN_FACING]
    ])
  })
})

describe('TOWN_FACING', () => {
  it('starts every walk facing the way the house’s door mats take Blue out', () => {
    const mat = rooms.RULES.house.exits[0]

    expect(rooms.warpOf({ at: mat.at, place: 'house' }, town.TOWN_FACING)).toBe(mat)
  })
})
