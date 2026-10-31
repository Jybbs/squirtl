import { type PropType, type VNode, defineComponent } from 'vue'

import * as learning from '../../../../lib/front/learning.ts'
import * as strip    from '../../../../lib/front/learning/strip.ts'
import { fillsOf }   from '../../../../lib/front/learning/tints.ts'
import { frameFor }  from '../../../../lib/game/actors.ts'
import { runsFor }   from '../../../../lib/game/screen.ts'
import type { Hue }  from '../../../../lib/identity/identity.ts'
import { count }     from '../../../../lib/widgets/numbers.ts'
import { HUES }      from '../../kit/hues.ts'
import { TICK }      from '../../kit/plots.tsx'

/**
 * Places a press along the strip, in the strip's own pixels.
 */
type Along = (press: number) => number

/**
 * The strip's geometry.
 */
const STRIP = strip.STRIP

/**
 * Blue standing split into the runs a pin draws.
 */
const blueRuns = runsFor(frameFor('player', 'down').grid)

/**
 * Draws the stretches of walk `n`, the table's solid in `hue` and the coin's in
 * the hatch of the pattern `id` names, each from its first press to its last
 * along `x`.
 */
function bands(hue: Hue, id: string, n: number, stretches: readonly learning.Stretch[], x: Along): VNode[] {
  return stretches.map(stretch => (
    <rect
      class={stretch.sure ? HUES[hue].fill : undefined}
      fill={stretch.sure ? undefined : `url(#${hatchOf(id, n)})`}
      height={STRIP.band}
      width={x(stretch.to) - x(stretch.from)}
      x={x(stretch.from)}
      y={STRIP.top + STRIP.row * n}
    />
  ))
}

/**
 * Draws a gridline and the count of presses beneath it at each of `ticks`.
 */
function gridlines(rows: strip.Rows, ticks: readonly number[], x: Along): VNode[] {
  return ticks.map(press => (
    <g>
      <line
        class="stroke-rule"
        stroke-width={STRIP.axis}
        x1={x(press)}
        x2={x(press)}
        y1={STRIP.top - STRIP.overhang}
        y2={rows.pins + STRIP.tile}
      />
      <text
        class={TICK}
        text-anchor={press === 0 ? 'start' : 'middle'}
        x={x(press)}
        y={rows.labels}
      >
        {count(press)}
      </text>
    </g>
  ))
}

/**
 * Names the hatch pattern of walk `n` among the patterns the prefix `id` names.
 */
function hatchOf(id: string, n: number): string {
  return `${id}-hatch-${n}`
}

/**
 * Declares the hatch of each walk's coin presses in its hue among `hues`, the
 * hue's mark read from the theme, under the names the prefix `id` gives them.
 */
function hatches(hues: readonly Hue[], id: string): string {
  return hues.map((hue, n) => strip.hatchMarkup(`var(--color-${hue}-mark)`, hatchOf(id, n))).join('')
}

/**
 * Draws the pin of a walk's Blue in `fills` on its tile centered at `center`,
 * in full where the walk has `ended` and faint before.
 */
function pin(center: number, ended: boolean, fills: readonly string[], rows: strip.Rows): VNode {
  return (
    <g>
      <rect
        class="fill-athens-gray stroke-rule"
        height={STRIP.tile}
        rx={STRIP.corner}
        stroke-width={STRIP.axis}
        width={STRIP.tile}
        x={center - STRIP.tile / 2}
        y={rows.pins}
      />
      <svg
        class={[ended ? 'opacity-100' : 'opacity-30', 'motion-safe:transition-opacity']}
        height={STRIP.pin}
        shape-rendering="crispEdges"
        viewBox="0 0 16 16"
        width={STRIP.pin}
        x={center - STRIP.pin / 2}
        y={rows.pins + (STRIP.tile - STRIP.pin) / 2}
      >
        {blueRuns.map(run => (
          <rect fill={fills[run.shade]} height={1} width={run.width} x={run.x} y={run.y} />
        ))}
      </svg>
    </g>
  )
}

/**
 * The parts of the strip that change only with its width, the walk picked out,
 * or a walk ending: the counts of presses beneath their gridlines, and each
 * walk's band, faint ahead of the clock and solid behind it, over the pin of
 * its Blue where it stops.
 */
export const WalkBands = defineComponent({
  name: 'WalkBands',

  props: {
    ended   : { required: true, type: Number },
    hues    : { required: true, type: Array as PropType<readonly Hue[]> },
    id      : { required: true, type: String },
    moments : { required: true, type: Array as PropType<readonly learning.Moment[]> },
    picked  : { default: null, type: Number as PropType<number | null> },
    width   : { required: true, type: Number }
  },

  setup: props => {
    const longest   = learning.longestOf(props.moments)
    const rows      = strip.stripRows(props.moments.length)
    const stretches = props.moments.map(moment => learning.stretchesOf(moment))
    const fills     = props.hues.map(hue => fillsOf(hue))
    const ticks     = strip.ticksOf(longest)

    return () => {
      const x: Along = press => props.width * press / longest
      return (
        <g>
          <defs innerHTML={hatches(props.hues, props.id)} />
          {gridlines(rows, ticks, x)}
          {props.moments.map((moment, n) => {
            const shown = props.picked === null || props.picked === n
            const band  = () => bands(props.hues[n]!, props.id, n, stretches[n]!, x)
            return (
              <g class={[shown ? 'opacity-100' : 'opacity-20', 'motion-safe:transition-opacity']}>
                <g class="opacity-20">{band()}</g>
                <g clip-path={`url(#${props.id}-reveal)`}>{band()}</g>
                {pin(x(moment.presses), (props.ended & 1 << n) > 0, fills[n]!, rows)}
              </g>
            )
          })}
        </g>
      )
    }
  }
})
