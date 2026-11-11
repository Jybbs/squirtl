import FONT                        from '../art/font.json' with { type: 'json' }
import { type Grid, spriteMarkup } from '../drawing/sprites.ts'
import { TILE, gridOf }            from '../game/text.ts'
import type { Agent }              from './results.ts'

/**
 * The runs of one agent and one start a mark names.
 */
type Marked = { agent: Agent, curriculum: boolean }

/**
 * The fill of each shade a glyph draws, every shade but the darkest left
 * clear and the darkest in the color of the text around it.
 */
const INK = ['none', 'none', 'none', 'currentColor'] as const

/**
 * Each agent's glyph from the game, solid for runs from the bedroom: the
 * menu's cursor for PPO, the text box's prompt for PQN, and a map's block for
 * the deep Q-network, the one the font draws no glyph for.
 */
const SOLID: Readonly<Record<Agent, Grid>> = {
  dqn : gridOf('007e7e7e7e7e7e00'),
  ppo : gridOf(FONT['▶']),
  pqn : gridOf(FONT['▼'])
}

/**
 * Each agent's glyph hollow for runs along the curriculum: the cursor as the
 * font draws it hollow, and the outline of each of the others.
 */
const HOLLOW: Readonly<Record<Agent, Grid>> = {
  dqn : outlineOf(SOLID.dqn),
  ppo : gridOf(FONT['▷']),
  pqn : outlineOf(SOLID.pqn)
}

/**
 * The outline of each agent's glyph as a path around the origin, which a plot
 * draws at an evaluation, since a glyph's pixels blur at the fractions of a
 * pixel a plot places its points at.
 */
export const SILHOUETTES: Readonly<Record<Agent, string>> = {
  dqn : 'M-4.5,-4.5H4.5V4.5H-4.5Z',
  ppo : 'M-3.5,-5.5L5,0L-3.5,5.5Z',
  pqn : 'M-5.5,-3.5H5.5L0,5Z'
}

/**
 * Draws the glyph marking the runs `marked` names as an SVG of the game's
 * pixels, in the color of the text around it.
 */
export function glyphOf({ agent, curriculum }: Marked): string {
  const grid = (curriculum ? HOLLOW : SOLID)[agent]
  return `<svg viewBox="0 0 ${TILE} ${TILE}" shape-rendering="crispEdges">`
       + `${spriteMarkup(grid, { fills: INK, size: 1, x: 0, y: 0 })}</svg>`
}

/**
 * Keeps each pixel `grid` sets that borders a clear pixel or the tile's edge,
 * the hollow form of a solid glyph.
 */
export function outlineOf(grid: Grid): Grid {
  const set = (y: number, x: number) => grid[y]?.[x] === '3'
  return grid.map((row, y) => [...row].map((shade, x) =>
    set(y, x) && !(set(y - 1, x) && set(y + 1, x) && set(y, x - 1) && set(y, x + 1)) ? shade : '0').join(''))
}
