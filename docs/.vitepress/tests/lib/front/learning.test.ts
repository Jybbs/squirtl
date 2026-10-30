import { describe, expect, it } from 'vitest'

import * as learning from '../../../lib/front/learning.ts'
import * as rooms    from '../../../lib/game/rooms.ts'
import * as town     from '../../../lib/game/town.ts'

/**
 * The walks the front page reads, read once for every case.
 */
const moments = learning.walksOf()

/**
 * A walk built by hand, its presses all the coin's but the last two, which
 * stops at the cap short of the north edge.
 */
const STOPPED: learning.Moment = {
  episodes : 2,
  presses  : 3,
  reached  : false,
  steps    : [
    { at: [5, 6], facing: 'down', sure: false },
    { at: [4, 6], facing: 'left', sure: true },
    { at: [4, 5], facing: 'up', sure: true },
    { at: [4, 4], facing: 'up', sure: false }
  ]
}

/**
 * Lists the square Blue stands on and the way he faces through the first
 * `presses` presses of a walk, from his door on.
 */
function placesOf(moment: learning.Moment, presses: number): Omit<learning.Footing, 'sure'>[] {
  return moment.steps.slice(0, presses + 1).map(({ at, facing }) => ({ at, facing }))
}

/**
 * Makes a table of the town's states holding `values` in the row of the door.
 */
function tableWith(values: readonly number[]): Float32Array {
  const q = new Float32Array(town.townStates * rooms.BUTTONS.length)
  q.set(values, town.townDoor * rooms.BUTTONS.length)
  return q
}

describe('walksOf', () => {
  it('reads walks of 204, 158, 50, and 18 presses, each reaching the north edge', () => {
    expect(moments.map(moment => [moment.episodes, moment.presses, moment.reached]))
      .toStrictEqual([[6, 204, true], [30, 158, true], [40, 50, true], [50, 18, true]])
  })

  it.each(moments)(
    'walks from Blue’s door after $episodes episodes a square a press until the north edge',
    moment => {
      const moves = moment.steps.slice(1).map((step, n) => {
        const from = moment.steps[n]!.at
        return Math.abs(step.at[0] - from[0]) + Math.abs(step.at[1] - from[1])
      })

      expect(moment.steps[0]).toMatchObject({ at: town.townStart, facing: town.TOWN_FACING })
      expect(moment.steps).toHaveLength(moment.presses + 1)
      expect(Math.max(...moves)).toBeLessThanOrEqual(1)
      expect(moment.steps.at(-1)!.at[1]).toBeLessThanOrEqual(rooms.NORTH_EDGE)
    }
  )

  it('reads the table after more episodes into a walk with fewer of the coin’s presses', () => {
    const coins = moments.map(moment => moment.steps.slice(0, -1).filter(step => !step.sure).length)

    expect(coins).toStrictEqual(coins.toSorted((a, b) => b - a))
    expect(coins.at(-1)).toBe(0)
  })

  it('walks the earlier moments together on the coin’s one seed until the table takes one over', () => {
    const [six, thirty] = moments
    const coined        = learning.stretchesOf(thirty!)[0]!.to

    expect(placesOf(thirty!, coined)).toStrictEqual(placesOf(six!, coined))
    expect(thirty!.steps[coined]!.sure).toBe(true)
  })
})

describe('walksOf facing', () => {
  it.each(moments)(
    'faces each press of the walk after $episodes episodes the way it went or would have gone',
    moment => {
      const presses = moment.steps.slice(1).map((step, n) => [moment.steps[n]!.at, step] as const)
      const moved   = presses.filter(([from, step]) => !rooms.same(from, step.at))

      expect(moved.filter(([from, step]) => !rooms.same(rooms.neighbor(from, step.facing), step.at)))
        .toStrictEqual([])
    }
  )

  it.each(moments)(
    'only turns Blue on his square wherever a press of the walk after $episodes episodes changes his facing',
    moment => {
      const presses = moment.steps.slice(1).map((step, n) => [moment.steps[n]!, step] as const)
      const turns   = presses.filter(([before, after]) => before.facing !== after.facing)

      expect(turns.length).toBeGreaterThan(0)
      expect(turns.filter(([before, after]) => !rooms.same(before.at, after.at))).toStrictEqual([])
    }
  )
})

describe('walksOf a moment of its own', () => {
  it('reads the same walk after 50 episodes whether or not it reads the earlier moments first', () => {
    expect(learning.walksOf({ ...learning.WALKING, moments: [50] })).toStrictEqual([moments.at(-1)])
  })
})

describe('favored', () => {
  it.each([
    ['no direction where the row holds no value', [0, 0, 0, 0, 0, 0], undefined],
    ['the direction ranked first', [0, 0.2, 0.5, 0, 0, 0], 2],
    ['the first of two tied', [0.3, 0, 0, 0.3, 0, 0], 0],
    ['no direction where only A and B hold a value', [0, 0, 0, 0, 0.9, 0.9], undefined]
  ])('chooses %s', (_, values, direction) => {
    expect(learning.favored(tableWith(values), town.townDoor)).toBe(direction)
  })
})

describe('stretchesOf', () => {
  it('splits a walk into the coin’s and the table’s presses, end to end', () => {
    expect(learning.stretchesOf(STOPPED)).toStrictEqual([
      { from: 0, sure: false, to: 1 }, { from: 1, sure: true, to: 3 }
    ])
  })

  it.each(moments)(
    'covers every press of the walk after $episodes episodes once, as the table or the coin chose it',
    moment => {
      const presses = learning.stretchesOf(moment)
        .flatMap(({ from, sure, to }) => Array.from({ length: to - from }, () => sure))

      expect(presses).toStrictEqual(moment.steps.slice(0, -1).map(step => step.sure))
    }
  )
})

describe('clockText', () => {
  it.each([
    [0, 'At 0 presses, the walks after 6, 30, 40, and 50 episodes are still under way'],
    [1, 'At 1 press, the walks after 6, 30, 40, and 50 episodes are still under way'],
    [18, 'At 18 presses, the walk after 50 episodes has reached the north edge, while the walks after 6, 30, '
       + 'and 40 episodes are still under way'],
    [50, 'At 50 presses, the walks after 40 and 50 episodes have reached the north edge, while the walks '
       + 'after 6 and 30 episodes are still under way'],
    [204, 'At 204 presses, the walks after 6, 30, 40, and 50 episodes have reached the north edge']
  ])('says where every walk stands at %i presses', (press, text) => {
    expect(learning.clockText(moments, press)).toBe(text)
    expect(text).toBePublishedProse()
  })

  it('names a walk stopped at the cap short of the north edge', () => {
    const text = learning.clockText([moments.at(-1)!, STOPPED], 18)

    expect(text).toBe('At 18 presses, the walk after 50 episodes has reached the north edge, while the walk '
                    + 'after 2 episodes has stopped short of it')
  })
})

describe('sceneLabel', () => {
  it('names the view and every moment’s episodes in published prose', () => {
    const label = learning.sceneLabel(moments)

    expect(label).toContain('after 6, 30, 40, and 50 episodes')
    expect(label).toBePublishedProse()
  })
})
