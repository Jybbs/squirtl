import { marks }      from '../../../../lib/front/reward.ts'
import * as climb     from '../../../../lib/front/reward/climb.ts'
import { drawReveal } from '../../kit/clock.tsx'
import { ROLES }      from '../../kit/hues.ts'
import * as plots     from '../../kit/plots.tsx'

/**
 * Draws the jump `jump` on the climb, the game's mark on a tile edged in its
 * term's hue beside its dot, dimmed while the step shown `at` falls short of
 * it.
 */
function drawJump(jump: climb.JumpMark, at: number) {
  const { dot, strokes, tile } = climb.CLIMB
  const role                   = ROLES[jump.term]

  return (
    <g
      class={['motion-safe:transition-opacity', jump.at > at && 'opacity-45']}
      key={`${jump.at}:${jump.dot[1]}`}
    >
      <rect
        class={['fill-athens-gray', role.stroke]}
        height={tile.side}
        rx={tile.radius}
        stroke-width={strokes.line}
        width={tile.side}
        x={jump.tile[0]}
        y={jump.tile[1]}
      />
      <svg
        height={tile.art}
        innerHTML={marks[jump.term]}
        width={tile.art}
        x={jump.mark[0]}
        y={jump.mark[1]}
      />
      <circle
        class={['stroke-ground', role.fill]}
        cx={jump.dot[0]}
        cy={jump.dot[1]}
        r={dot}
        stroke-width={strokes.line}
      />
    </g>
  )
}

/**
 * Draws the return's climb `drawn` up to the step `at`, filling the box it sits
 * in: the whole course in the color of ground not yet covered, the part played
 * over it in the agent's hue through the clip `clip` names, a tick along the
 * floor for each new position, each jump's mark, and the step shown.
 */
export function drawClimb(drawn: climb.ClimbPlot, at: number, clip: string) {
  const { halo, head, reach } = climb.CLIMB
  const [x, y]                = drawn.heads[at]!

  return (
    <svg {...plots.SVG} viewBox={`0 0 ${drawn.width} ${drawn.height}`}>
      {drawReveal(drawn.height, clip, x + reach)}
      {plots.drawAxis(drawn.axis)}
      {[...drawn.values, ...drawn.steps].map(label => plots.drawLabel(label))}
      {plots.drawLabel(drawn.title, plots.TITLE)}
      <path class="fill-none stroke-rule" d={drawn.rug} {...plots.CURVE} />
      <path class="fill-none stroke-ahead" d={drawn.course} {...plots.CURVE} />
      <g clip-path={`url(#${clip})`}>
        <path class={['fill-none', ROLES.novelty.stroke]} d={drawn.rug} {...plots.CURVE} />
        <path class={['fill-none', ROLES.agent.stroke]} d={drawn.course} {...plots.CURVE} />
      </g>
      {drawn.jumps.map(jump => drawJump(jump, at))}
      <circle class={[ROLES.agent.fill, 'opacity-16']} cx={x} cy={y} r={halo} />
      <circle class={ROLES.agent.fill} cx={x} cy={y} r={head} />
    </svg>
  )
}
