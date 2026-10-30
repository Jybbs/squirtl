import type { VNode } from 'vue'

import type { PlotLabel } from '../../../lib/drawing/plot.ts'
import { IDENTITY }       from '../../../lib/identity/identity.ts'

/**
 * The attributes of a plot's curve, its joins rounded and its stroke the
 * identity's line.
 */
export const CURVE = { 'stroke-linejoin': 'round', 'stroke-width': IDENTITY.lengths.strokes.line } as const

/**
 * The attributes of a plot's SVG, which fills the box it sits in and is hidden
 * from a screen reader.
 */
export const SVG = { 'aria-hidden': 'true', 'class': 'absolute size-full overflow-visible' } as const

/**
 * The classes of a count, a value, or a step labeling a plot's axes.
 */
export const TICK = 'fill-quiet font-code text-label tabular-nums'

/**
 * The classes of the title a plot sets along its axis.
 */
export const TITLE = 'fill-ink font-body text-small'

/**
 * Draws the path `d` of a plot's axis or gridlines in the rule, at the
 * identity's stroke for an axis.
 */
export function drawAxis(d: string): VNode {
  return <path class="fill-none stroke-rule" d={d} stroke-width={IDENTITY.lengths.strokes.axis} />
}

/**
 * Draws `label` at its point in the classes `look` gives it, a tick's unless
 * given another, its text on the side its anchor names.
 */
export function drawLabel(label: PlotLabel, look: string = TICK): VNode {
  return (
    <text class={look} key={`${label.text}:${label.x}`} text-anchor={label.anchor} x={label.x} y={label.y}>
      {label.text}
    </text>
  )
}
