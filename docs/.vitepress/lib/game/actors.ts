import { type Grid, spriteMarkup } from '../drawing/sprites.ts'
import * as identity               from '../identity/identity.ts'
import type { Episode, Term }      from './episode.ts'
import type { Stance }             from './gait.ts'
import * as rooms                  from './rooms.ts'

/**
 * Someone standing in a room, or a Poké Ball on Oak's table, beside the way it
 * faces and the stance of its walk it shows.
 */
export interface Actor {
  at     : rooms.Square
  facing : rooms.Direction
  name   : Sprite
  stance : Stance
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
 * frames, the right-facing frames being the left-facing ones mirrored, as
 * pret/pokered's `SpriteFacingAndAnimationTable` draws them in
 * `data/sprites/facings.asm` lines 3 to 18.
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
  mom   : { at: [5, 4], facing: 'left', name: 'mom', stance: 'standing' },
  oak   : { at: [5, 2], facing: 'down', name: 'oak', stance: 'standing' },
  rival : { at: [4, 3], facing: 'down', name: 'rival', stance: 'standing' }
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
  .map(at => ({ at, facing: 'down', name: 'ball', stance: 'standing' }))

/**
 * Every pose of every sprite in each stance of its walk in each direction,
 * built once as the module loads.
 */
const poses = Object.fromEntries(Object.entries(identity.IDENTITY.sprites).map(([name, { frames }]) => [
  name,
  Object.fromEntries(rooms.DIRECTIONS.map(facing => [facing, posesOf(frames, facing)]))
])) as Readonly<Record<Sprite, Readonly<Record<rooms.Direction, Readonly<Record<Stance, Pose>>>>>>

/**
 * Chooses the frames of `frames` a sprite shows facing `facing` in each stance
 * of its walk, a sprite of three frames standing in all of them and a sprite of
 * one showing it whichever way it faces. Walking on the other foot mirrors the
 * walking frame facing down or up, as `.FlippedOAM` does, and keeps it as it is
 * facing left or right, the right-facing frames being mirrored already.
 */
function posesOf(frames: readonly Grid[], facing: rooms.Direction): Readonly<Record<Stance, Pose>> {
  const standing = frames[FACING[facing][0]] ?? frames[0]!
  const walking  = frames[FACING[facing][1]]
  const mirrored = facing === 'right'
  return {
    mirrored : walking ? { grid: walking, mirrored: facing !== 'left' } : { grid: standing, mirrored },
    standing : { grid: standing, mirrored },
    walking  : { grid: walking ?? standing, mirrored }
  }
}

/**
 * Lists who stands in the room `episode` stands in, in the order they draw: Mom
 * in the house, Oak at his table in the lab, the rival, the Poké Balls still on
 * the table, and Oak at `leaderAt` in `stance` while he leads Blue there.
 */
export function actorsOf(episode: Episode, leaderAt?: rooms.Square, stance: Stance = 'standing'): Actor[] {
  const leader          = episode.leader?.place === episode.place ? episode.leader : null
  const actors: Actor[] = []
  if (episode.place === 'house') actors.push(PEOPLE.mom)
  if (episode.place === 'lab') {
    const table = balls.filter(ball => !episode.chosen || !rooms.same(ball.at, episode.chosen))
    if (!leader) actors.push(PEOPLE.oak)
    actors.push(PEOPLE.rival, ...table)
  }
  if (leader) actors.push({ at: leaderAt ?? leader.at, facing: leader.facing, name: 'oak', stance })
  return actors
}

/**
 * Reads the frame `name` shows facing `facing` in `stance`, standing unless
 * given another.
 */
export function frameFor(name: Sprite, facing: rooms.Direction, stance: Stance = 'standing'): Pose {
  return poses[name][facing][stance]
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
