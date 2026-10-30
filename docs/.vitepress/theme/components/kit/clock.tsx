import type { VNode } from 'vue'

import { IDENTITY } from '../../../lib/identity/identity.ts'

/**
 * The clock chip's lengths in the pixels of the drawing it sits in: its height,
 * the baseline of its reading, its corners' radius, and the width of the rule
 * on its leading edge.
 */
const CLOCK_CHIP = {
  baseline : 14,
  corner   : IDENTITY.lengths.radii['1'],
  height   : 20,
  rule     : IDENTITY.lengths.borders.bar
} as const

/**
 * Draws the chip naming a clock's reading `text` in a drawing, its left edge at
 * `left` and `width` wide, a rule in the ink on its leading edge over a ground
 * of the ink mixed into the page's.
 */
export function drawClockChip(left: number, text: string, width: number): VNode {
  const { baseline, corner, height, rule } = CLOCK_CHIP

  return (
    <g transform={`translate(${left} 0)`}>
      <rect class="clock-chip" height={height} rx={corner} width={width} />
      <rect class="fill-ink" height={height} width={rule} />
      <text
        class="fill-ink font-code text-label font-medium tabular-nums"
        text-anchor="middle"
        x={(width + rule) / 2}
        y={baseline}
      >
        {text}
      </text>
    </g>
  )
}

/**
 * Draws a clock's line in the ink at `x`, from `top` down to `bottom`, at the
 * identity's stroke for a reference line.
 */
export function drawClockLine(bottom: number, top: number, x: number): VNode {
  return (
    <line
      class="stroke-ink"
      stroke-width={IDENTITY.lengths.strokes.reference}
      x1={x}
      x2={x}
      y1={top}
      y2={bottom}
    />
  )
}

/**
 * Declares the clip `id` names, which shows a drawing `height` pixels tall from
 * its left edge to `width`, the clock's reach along it.
 */
export function drawReveal(height: number, id: string, width: number): VNode {
  return (
    <defs>
      <clipPath id={id}>
        <rect height={height} width={width} />
      </clipPath>
    </defs>
  )
}
