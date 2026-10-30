import WORLD from '../art/world.json' with { type: 'json' }

/**
 * A button of the Game Boy's that a press chooses.
 */
export type Button = (typeof BUTTONS)[number]

/**
 * A direction Blue faces and walks in.
 */
export type Direction = (typeof DIRECTIONS)[number]

/**
 * A room of the model, among Blue's bedroom, the house below it, Pallet Town,
 * and Oak's lab.
 */
export type Place = keyof typeof WORLD

/**
 * What a room holds beyond the squares its walk grid marks walkable: the
 * squares a person, a Poké Ball, or a closed door blocks, the warps a step
 * takes, the door mats a press of Down leaves by, and the Poké Balls on Oak's
 * table.
 */
export interface Rules {
  blocked : readonly Square[]
  warps   : readonly Warp[]
  balls?  : readonly Square[]
  exits?  : readonly Warp[]
}

/**
 * A square of a room, counted in sixteen-pixel squares from its top left.
 */
export type Square = readonly [x: number, y: number]

/**
 * Where someone stands, a room and a square in it.
 */
export interface Standing {
  at    : Square
  place : Place
}

/**
 * A square that moves Blue to the room `to` names, where he stands at `arrive`,
 * `at` being the square he steps onto, or for a door mat the square he presses
 * Down on.
 */
export interface Warp {
  arrive : Square
  at     : Square
  to     : Place
}

/**
 * The four directions in the order a random press draws them, the order the
 * buttons list them in.
 */
export const DIRECTIONS = ['up', 'down', 'left', 'right'] as const

/**
 * The squares Blue walks inside the lab behind Oak, from its door up to the
 * table.
 */
export const LAB_ENTRY: readonly Square[] = [
  [5, 11], [5, 10], [5, 9], [5, 8], [5, 7], [5, 6], [5, 5], [5, 4], [5, 3]
]

/**
 * The square each direction moves Blue by, in the order a route search tries
 * them.
 */
export const MOVES: Readonly<Record<Direction, Square>> = {
  down  : [0, 1],
  left  : [-1, 0],
  right : [1, 0],
  up    : [0, -1]
}

/**
 * The row of Pallet Town's north edge, where pret/pokered's
 * `PalletTownDefaultScript` reads `wYCoord` and has Oak stop Blue.
 */
export const NORTH_EDGE = 1

/**
 * The squares Blue walks behind Oak once Oak stops him, from his own square on
 * the north edge to the lab's door.
 */
export const OAK_LEADS = [
  [10, 1], [10, 2], [10, 3], [10, 4], [10, 5], [10, 6], [10, 7], [9, 7], [9, 8], [9, 9], [9, 10], [9, 11],
  [9, 12], [10, 12], [11, 12], [12, 12]
] as const satisfies readonly Square[]

/**
 * Each room's warps and door mats as pret/pokered's `data/maps/objects` places
 * them, beside the squares Mom, Oak, the rival, the Poké Balls, the lab's door,
 * and the rival's door block. A warp leaves Blue facing the way he walked onto
 * it, since no map load resets the player's facing, and the mats put him on
 * Pallet Town's door at 5, 5, from which `PlayerStepOutFromDoor` walks him down
 * to 5, 6.
 */
export const RULES = {
  bedroom : { blocked: [], warps: [{ arrive: [7, 1], at: [7, 1], to: 'house' }] },
  lab     : { balls: [[6, 3], [7, 3], [8, 3]], blocked: [[5, 2], [4, 3], [6, 3], [7, 3], [8, 3]], warps: [] },
  pallet  : { blocked: [[12, 11], [13, 5]], warps: [{ arrive: [2, 7], at: [5, 5], to: 'house' }] },
  house   : {
    blocked : [[5, 4]],
    exits   : [{ arrive: [5, 6], at: [2, 7], to: 'pallet' }, { arrive: [5, 6], at: [3, 7], to: 'pallet' }],
    warps   : [{ arrive: [7, 1], at: [7, 1], to: 'bedroom' }]
  }
} as const satisfies Readonly<Record<Place, Rules>>

/**
 * The buttons a press chooses among, the directions first and then A and B, in
 * the order a random press and a learner's table index them.
 */
export const BUTTONS = [...DIRECTIONS, 'a', 'b'] as const

/**
 * Finds the Poké Ball on the square `from` faces in `facing`, where one stands
 * there.
 */
export function ballAhead(from: Standing, facing: Direction): Square | undefined {
  const ahead        = neighbor(from.at, facing)
  const rules: Rules = RULES[from.place]
  return rules.balls?.find(ball => same(ball, ahead))
}

/**
 * Reads the direction a step from `from` to `to` takes, a step with no sideways
 * part reading as down where it descends and as up otherwise.
 */
export function heading(from: Square, to: Square): Direction {
  return to[0] > from[0] ? 'right' : to[0] < from[0] ? 'left' : to[1] > from[1] ? 'down' : 'up'
}

/**
 * Finds the square one step from `at` in `direction`.
 */
export function neighbor(at: Square, direction: Direction): Square {
  return [at[0] + MOVES[direction][0], at[1] + MOVES[direction][1]]
}

/**
 * Reports whether Blue can stand on `at` in `place`, a square the room's walk
 * grid marks walkable and nothing in the room blocks.
 */
export function passable(at: Square, place: Place): boolean {
  return WORLD[place].walk[at[1]]?.[at[0]] === '1' && !RULES[place].blocked.some(cell => same(cell, at))
}

/**
 * Finds the directions that walk Blue the shortest way from where `from` stands
 * to `to` in the same room, through a breadth-first search that treats `to` as
 * walkable even where a door stands on it, and finds none where `to` is out of
 * reach.
 */
export function routeMoves(from: Standing, to: Square): Direction[] {
  const width = WORLD[from.place].w
  const key   = ([x, y]: Square): number => y * width + x
  const back  = new Map<number, readonly [Square, Direction] | null>([[key(from.at), null]])
  const queue = [from.at]
  // Reads each square the queue gains while the loop runs.
  for (const at of queue) {
    if (same(at, to)) break
    for (const direction of Object.keys(MOVES) as Direction[]) {
      const next = neighbor(at, direction)
      if ((!passable(next, from.place) && !same(next, to)) || back.has(key(next))) continue
      back.set(key(next), [at, direction])
      queue.push(next)
    }
  }
  const moves: Direction[] = []
  for (let link = back.get(key(to)); link; link = back.get(key(link[0]))) moves.unshift(link[1])
  return moves
}

/**
 * Reports whether `a` and `b` name one square.
 */
export function same(a: Square, b: Square): boolean {
  return a[0] === b[0] && a[1] === b[1]
}

/**
 * Finds the warp a press of `direction` takes Blue through from where `from`
 * stands, a door mat under him where the press is Down and otherwise a warp on
 * the square ahead.
 */
export function warpOf(from: Standing, direction: Direction): Warp | undefined {
  const rules: Rules = RULES[from.place]
  const ahead        = neighbor(from.at, direction)
  return (direction === 'down' ? rules.exits?.find(exit => same(exit.at, from.at)) : undefined)
      ?? rules.warps.find(warp => same(warp.at, ahead))
}
