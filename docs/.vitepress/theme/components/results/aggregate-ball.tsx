import type { VNode } from 'vue'

import { runsOf }   from '../../../lib/drawing/sprites.ts'
import { IDENTITY } from '../../../lib/identity/identity.ts'

/**
 * The classes inking a Poké Ball whose top is left empty, every shade but its
 * edge in the raised ground.
 */
const EMPTY = ['fill-lift', 'fill-lift', 'fill-lift', 'fill-quiet'] as const
/**
 * The classes inking each of the Game Boy's four shades a sprite takes, its
 * white in the raised ground, its light shade in the current color half
 * clear, its dark shade in the current color, and its black in the ink.
 */
const SHADES = ['fill-lift', 'fill-current opacity-45', 'fill-current', 'fill-ink'] as const
/**
 * The runs of the Poké Ball's first frame.
 */
const ballRuns = runsOf(IDENTITY.sprites.ball.frames[0]!)
/**
 * The count of pixels on each side of the Poké Ball.
 */
export const ballSide = IDENTITY.sprites.ball.frames[0]!.length

/**
 * Draws the Poké Ball with its top-left pixel at `x` on the top of its
 * group, each pixel `size` on a side, its shades in the current color and the
 * ink, or with its top left empty where `empty` is set.
 */
export function drawBall(size: number, x: number, empty = false): VNode {
  const shades = empty ? EMPTY : SHADES
  return (
    <g>
      {ballRuns.map(run => (
        <rect
          class={shades[run.shade]}
          height={size + 0.3}
          width={run.width * size + 0.3}
          x={x + run.x * size}
          y={run.y * size}
        />
      ))}
    </g>
  )
}
