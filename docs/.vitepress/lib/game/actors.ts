import { type Grid, spriteMarkup } from '../drawing/sprites.ts'
import * as identity               from '../identity/identity.ts'
import type { Episode, Term }      from './episode.ts'
import * as rooms                  from './rooms.ts'

/**
 * Someone standing in a room, or a Poké Ball on Oak's table, beside the way it
 * faces and whether it shows its walking frame.
 */
export interface Actor {
  at       : rooms.Square
  facing   : rooms.Direction
  name     : Sprite
  stepping : boolean
}

/**
 * One frame of a sprite and whether it draws mirrored, the way a frame facing
 * left turns to face right.
 */
export interface Pose {
  grid     : Grid
  mirrored : boolean
}

/**
 * A sprite the identity declares.
 */
export type Sprite = keyof identity.Identity['sprites']

/**
 * The frame each facing shows standing and walking, as indexes into a sprite's
 * frames, the right-facing frames being the left-facing ones mirrored.
 */
const FACING: Readonly<Record<rooms.Direction, readonly [standing: number, walking: number]>> = {
  down  : [0, 3],
  left  : [2, 5],
  right : [2, 5],
  up    : [1, 4]
}

/**
 * Where Mom, Oak, and the rival stand as pret/pokered's `data/maps/objects`
 * places them, each facing the way the game first draws them.
 */
const PEOPLE = {
  mom   : { at: [5, 4], facing: 'left', name: 'mom', stepping: false },
  oak   : { at: [5, 2], facing: 'down', name: 'oak', stepping: false },
  rival : { at: [4, 3], facing: 'down', name: 'rival', stepping: false }
} as const satisfies Record<string, Actor>

/**
 * The mark of a new position, a dot in the current color.
 */
const STEP_DOT = '<svg viewBox="0 0 12 12"><circle cx="6" cy="6" r="3" fill="currentColor"/></svg>'

/**
 * The sprite each term of the reward is marked by, Oak for a milestone and the
 * Poké Ball for the starter, and none for a new position, which the dot marks.
 */
const TERM_SPRITES = {
  milestone : 'oak',
  novelty   : null,
  starter   : 'ball'
} as const satisfies Record<Term, Sprite | null>

/**
 * The Poké Balls on Oak's table.
 */
const balls: readonly Actor[] = rooms.RULES.lab.balls
  .map(at => ({ at, facing: 'down', name: 'ball', stepping: false }))

/**
 * Every pose of every sprite, standing and then walking in each direction,
 * built once as the module loads.
 */
const poses = Object.fromEntries(Object.entries(identity.IDENTITY.sprites).map(([name, { frames }]) => [
  name,
  Object.fromEntries(rooms.DIRECTIONS.map(facing => [facing, posesOf(frames, facing)]))
])) as Readonly<Record<Sprite, Readonly<Record<rooms.Direction, readonly [Pose, Pose]>>>>

/**
 * Chooses the frames of `frames` a sprite shows facing `facing`, standing and
 * then walking, a sprite of three frames standing for both and a sprite of one
 * showing it whichever way it faces.
 */
function posesOf(frames: readonly Grid[], facing: rooms.Direction): readonly [Pose, Pose] {
  const standing = frames[FACING[facing][0]] ?? frames[0]!
  const walking  = frames[FACING[facing][1]] ?? standing
  const mirrored = facing === 'right'
  return [{ grid: standing, mirrored }, { grid: walking, mirrored }]
}

/**
 * Lists who stands in the room `episode` stands in, in the order they draw: Mom
 * in the house, Oak at his table in the lab, the rival, the Poké Balls still on
 * the table, and Oak at `leaderAt` while he leads Blue there.
 */
export function actorsOf(episode: Episode, leaderAt?: rooms.Square, stepping = false): Actor[] {
  const leader          = episode.leader?.place === episode.place ? episode.leader : null
  const actors: Actor[] = []
  if (episode.place === 'house') actors.push(PEOPLE.mom)
  if (episode.place === 'lab') {
    const table = balls.filter(ball => !episode.chosen || !rooms.same(ball.at, episode.chosen))
    if (!leader) actors.push(PEOPLE.oak)
    actors.push(PEOPLE.rival, ...table)
  }
  if (leader) actors.push({ at: leaderAt ?? leader.at, facing: leader.facing, name: 'oak', stepping })
  return actors
}

/**
 * Reads the frame `name` shows facing `facing`, its walking frame where
 * `stepping` is set and the sprite carries one.
 */
export function frameFor(name: Sprite, facing: rooms.Direction, stepping = false): Pose {
  return poses[name][facing][Number(stepping)]!
}

/**
 * Draws the first frame of `name` as an SVG mark in `fills`, the Game Boy's
 * shades unless given others.
 */
export function spriteMark(name: Sprite, fills: readonly string[] = identity.spriteShades): string {
  const { grid } = frameFor(name, 'down')
  const markup   = spriteMarkup(grid, { fills, size: 1, x: 0, y: 0 })
  return `<svg viewBox="0 0 ${grid.length} ${grid.length}" shape-rendering="crispEdges">${markup}</svg>`
}

/**
 * Draws the mark of the reward's term `term`: a dot for a new position, Oak for
 * a milestone, and the Poké Ball for the starter.
 */
export function termMark(term: Term): string {
  const sprite = TERM_SPRITES[term]
  return sprite ? spriteMark(sprite) : STEP_DOT
}
