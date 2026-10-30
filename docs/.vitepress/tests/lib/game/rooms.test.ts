import { describe, expect, it } from 'vitest'

import * as rooms from '../../../lib/game/rooms.ts'

describe('BUTTONS', () => {
  it('lists the directions first, in the order a random press draws them, then A and B', () => {
    expect(rooms.BUTTONS).toStrictEqual(['up', 'down', 'left', 'right', 'a', 'b'])
  })
})

describe('MOVES', () => {
  it('moves Blue one square in the direction each names', () => {
    expect(Object.values(rooms.MOVES).map(([dx, dy]) => Math.abs(dx) + Math.abs(dy)))
      .toStrictEqual([1, 1, 1, 1])
    expect(Object.keys(rooms.MOVES).toSorted()).toStrictEqual(rooms.DIRECTIONS.toSorted())
  })
})

describe('passable', () => {
  it.each([
    ['bedroom', [3, 6], true, 'the square Blue wakes on'],
    ['bedroom', [3, 5], false, 'a square the walk grid marks blocked'],
    ['house', [5, 4], false, 'Mom’s square'],
    ['lab', [7, 3], false, 'Squirtle’s Poké Ball'],
    ['lab', [5, 2], false, 'Oak’s square at his table'],
    ['pallet', [5, 5], true, 'the door of Blue’s house, a warp'],
    ['pallet', [12, 11], false, 'the lab’s door'],
    ['pallet', [-1, 6], false, 'a square off the west edge'],
    ['pallet', [20, 6], false, 'a square off the east edge'],
    ['pallet', [5, 18], false, 'a square off the south edge']
  ] as const)('reads %s at %j as %s, %s', (place, at, walkable, _square) => {
    expect(rooms.passable(at, place)).toBe(walkable)
  })
})

describe('heading', () => {
  it.each([
    [[3, 6], [4, 6], 'right'],
    [[3, 6], [2, 6], 'left'],
    [[3, 6], [3, 7], 'down'],
    [[3, 6], [3, 5], 'up'],
    [[3, 6], [3, 6], 'up']
  ] as const)('reads a step from %j to %j as %s', (from, to, way) => {
    expect(rooms.heading(from, to)).toBe(way)
  })
})

describe('neighbor', () => {
  it.each([
    ['right', [4, 6]],
    ['left', [2, 6]],
    ['down', [3, 7]],
    ['up', [3, 5]]
  ] as const)('steps from 3, 6 %s to %j', (way, to) => {
    expect(rooms.neighbor([3, 6], way)).toStrictEqual(to)
  })
})

describe('routeMoves', () => {
  it.each([
    ['bedroom', [3, 6], [7, 1], ['right', 'right', 'up', 'right', 'right', 'up', 'up', 'up', 'up']],
    ['pallet', [5, 6], [10, 1], ['right', 'right', 'right', 'right', 'right', 'up', 'up', 'up', 'up', 'up']],
    ['lab', [5, 3], [7, 3], ['down', 'right', 'right', 'up']],
    ['pallet', [5, 6], [5, 5], ['up']],
    ['pallet', [0, 0], [10, 1], []],
    ['pallet', [5, 6], [5, 6], []]
  ] as const)('walks %s from %j to %j by %j', (place, at, to, moves) => {
    expect(rooms.routeMoves({ at, place }, to)).toStrictEqual(moves)
  })
})

describe('warpOf', () => {
  it.each([
    ['bedroom', [7, 2], 'up', { arrive: [7, 1], at: [7, 1], to: 'house' }],
    ['house', [2, 7], 'down', { arrive: [5, 6], at: [2, 7], to: 'pallet' }],
    ['house', [3, 7], 'down', { arrive: [5, 6], at: [3, 7], to: 'pallet' }],
    ['house', [2, 7], 'left', undefined],
    ['pallet', [5, 6], 'up', { arrive: [2, 7], at: [5, 5], to: 'house' }],
    ['lab', [5, 4], 'down', undefined]
  ] as const)('takes Blue from %s at %j pressing %s through %j', (place, at, direction, warp) => {
    expect(rooms.warpOf({ at, place }, direction)).toStrictEqual(warp)
  })
})

describe('ballAhead', () => {
  it.each([
    ['lab', [7, 4], 'up', [7, 3]],
    ['lab', [5, 3], 'right', [6, 3]],
    ['lab', [5, 4], 'up', undefined],
    ['house', [5, 5], 'up', undefined]
  ] as const)('finds the Poké Ball %s at %j faces %s as %j', (place, at, facing, ball) => {
    expect(rooms.ballAhead({ at, place }, facing)).toStrictEqual(ball)
  })
})
