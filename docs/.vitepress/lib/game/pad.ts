import type { Button } from './rooms.ts'
import { runsAt }      from './text.ts'

/**
 * One press a step makes, a button or no press at all.
 */
export type Press = Button | null

/**
 * The rectangle of the direction pad's cross each arm fills, as its left, top,
 * width, and height on a mark 16 pixels across.
 */
const ARMS = {
  down  : [6, 10, 4, 5],
  left  : [1, 6, 5, 4],
  right : [10, 6, 5, 4],
  up    : [6, 1, 4, 5]
} as const

/**
 * The name a reader reads for each press.
 */
const NAMES = { a: 'A', b: 'B', down: 'Down', left: 'Left', right: 'Right', up: 'Up' } as const

/**
 * Reads the name of `press`.
 */
export const pressName = (press: Press): string => press === null ? 'No press' : NAMES[press]

/**
 * Draws `press` as a mark in the current color, the Game Boy's direction pad
 * with the pressed arm filled, the A or the B button holding its letter in the
 * game's font, or an empty pad standing for no press.
 */
export function padMark(press: Press): string {
  const open = '<svg viewBox="0 0 16 16" shape-rendering="crispEdges">'
  if (press === 'a' || press === 'b') {
    const letter = runsAt(NAMES[press]).map(run =>
      `<rect x="${4 + run.x}" y="${4 + run.y}" width="${run.width}" height="1" class="fill-ground"/>`).join('')
    return `${open}<circle cx="8" cy="8" r="7" fill="currentColor"/>${letter}</svg>`
  }
  const arm   = press === null ? null : ARMS[press]
  const cross = `<path d="M6 1h4v5h5v4h-5v5h-4v-5h-5v-4h5z" fill="currentColor" opacity="${arm ? 0.32 : 0.55}"/>`
  const fill  = arm ? `<rect x="${arm[0]}" y="${arm[1]}" width="${arm[2]}" height="${arm[3]}" fill="currentColor"/>` : ''
  return `${open}${cross}${fill}</svg>`
}
