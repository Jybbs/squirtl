import { defineComponent, ref } from 'vue'

import * as order                from '../../../lib/identity/order.ts'
import { fixed }                 from '../../../lib/widgets/numbers.ts'
import { ROLES }                 from '../kit/hues.ts'
import { CURVE, TICK, drawAxis } from '../kit/plots.tsx'

/**
 * The values the plate's rules stand at.
 */
const RULES = [0, 0.5, 1]

/**
 * The size of a switch's chart, which its line stretches to fill, and the
 * margins it leaves above and below its lines.
 */
const MINI = { height: 40, margins: { bottom: 2, left: 0, right: 0, top: 2 }, width: 96 }

/**
 * The radius of the pen's nib, and how far a figure stands from the rule or
 * the edge it labels.
 */
const SPACING = { figure: 8, foot: 6, nib: 4, rise: 4 }

/**
 * The pen's state, as `usePen` holds it.
 */
type Pen = ReturnType<typeof order.usePen>

/**
 * Writes the path of `run`'s line across a switch's chart.
 */
const mini = (run: order.Run) => order.pathOf(order.pointsOf(run, MINI.width, MINI.height, MINI.margins))

/**
 * Draws the plate, its rules with their figures, its ends, each line as far as
 * the pen has drawn it, and the nib where the pen stands.
 */
function drawPlate({ height, lines, pen, width }: Pen) {
  const y      = (value: number) => order.yOf(value, height.value, order.PLATE)
  const active = lines.value.find(line => line.run.hue === pen.active)
  const nib    = active && order.pointAt(active.points, pen.drawn[active.run.hue])

  return (
    <svg aria-label="Made-up runs, one line per series hue, drawn on in the order" class="block h-auto w-full" role="img" viewBox={`0 0 ${width.value} ${height.value}`}>
      {RULES.map(value => [
        drawAxis(`M${order.PLATE.left},${y(value)}H${width.value - order.PLATE.right}`),
        <text class={TICK} text-anchor="end" x={order.PLATE.left - SPACING.figure} y={y(value) + SPACING.rise}>{fixed(value, 1)}</text>
      ])}
      <text class={TICK} x={order.PLATE.left} y={height.value - SPACING.foot}>0</text>
      <text class={TICK} text-anchor="end" x={width.value - order.PLATE.right} y={height.value - SPACING.foot}>2.5M steps</text>
      {lines.value.map(({ points, run }) => (
        <path
          {...CURVE}
          class={['fill-none', ROLES[run.role].stroke]}
          d={order.pathOf(points)}
          pathLength={1}
          stroke-dasharray="1 2"
          stroke-dashoffset={1 - pen.drawn[run.hue]}
          stroke-linecap="round"
          visibility={pen.drawn[run.hue] > 0 ? 'visible' : 'hidden'}
        />
      ))}
      {nib && <circle class={['identity-nib', ROLES[active.run.role].fill]} cx={nib[0]} cy={nib[1]} r={SPACING.nib} />}
    </svg>
  )
}

/**
 * Draws a switch for each made-up run, a chart of its line among the others
 * beside its place, its hue, and its role.
 */
function drawSwitches({ switches }: Pen) {
  return (
    <div {...switches.root.value} aria-label="Show or hide each series" class="identity-switches grid gap-2">
      {order.RUNS.map(run => (
        <button
          {...switches.item(run.hue)}
          aria-label={`${order.tagOf(run)}, ${order.ROLE_WORDS[run.role].toLowerCase()}`}
          class="identity-switch focus-ring grid min-w-0 cursor-pointer content-start gap-0 rounded-2 border-hairline border-rule p-2 text-left text-ink"
          type="button"
        >
          <svg aria-hidden="true" class="block h-6 w-full" preserveAspectRatio="none" viewBox={`0 0 ${MINI.width} ${MINI.height}`}>
            {order.RUNS.filter(other => other !== run).map(other => <path class="identity-other fill-none stroke-rule" d={mini(other)} />)}
            <path class={['identity-line fill-none', ROLES[run.role].stroke]} d={mini(run)} />
          </svg>
          <span class="font-code text-label font-medium">{order.tagOf(run)}</span>
          <span class="font-body text-label text-quiet">{order.ROLE_WORDS[run.role]}</span>
        </button>
      ))}
    </div>
  )
}

/**
 * One made-up run for each series hue on a plate, a pen drawing each line on
 * in the order the identity takes the hues, a switch for each hue showing its
 * line among the others and its place, its hue, and its role, and a press on
 * Draw them again rewinding every line from wherever the pen stands before it
 * draws them on again.
 */
export const IdentityOrder = defineComponent({
  name  : 'IdentityOrder',
  setup : () => {
    const box   = ref<HTMLElement>()
    const state = order.usePen(box)

    return () => (
      <div class="@container grid gap-3">
        <div class="rounded-2 border-hairline border-rule" ref={box}>{drawPlate(state)}</div>
        {drawSwitches(state)}
        <div class="flex justify-end">
          <button class="identity-again focus-ring cursor-pointer rounded-1 border-hairline border-rule px-3 py-1 text-small text-ink" onClick={state.again} type="button">
            Draw them again
          </button>
        </div>
      </div>
    )
  }
})
