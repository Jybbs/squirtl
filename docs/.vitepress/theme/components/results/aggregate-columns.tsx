import { type VNode, defineComponent } from 'vue'

import { IDENTITY }              from '../../../lib/identity/identity.ts'
import * as aggregateColumns     from '../../../lib/results/aggregate-columns.ts'
import { committedSeeds }        from '../../../lib/results/aggregate-switches.ts'
import * as aggregate            from '../../../lib/results/aggregate.ts'
import { AGENTS, type Estimate } from '../../../lib/results/results.ts'
import { HUES }                  from '../kit/hues.ts'
import { SVG, TICK, drawAxis }   from '../kit/plots.tsx'
import { ballSide, drawBall }    from './aggregate-ball.tsx'

/**
 * Where one column stands and what it shows: what the plot gives every
 * column, whether its runs are open, its width, and its middle.
 */
interface Place extends Pick<Plot, 'popped' | 'seeds' | 'still' | 'toggle'> {
  open : boolean
  step : number
  x    : number
}

/**
 * What the plot draws and where it sets each part that moves: each column's
 * Poké Ball by its place, random presses' band, the columns, the place of the
 * column whose runs are open, the lists each run's Poké Ball is set in by
 * seed, random presses' estimate, the seeds kept, whether figures land at
 * once, and the call switching a seed from one of its runs.
 */
export interface Plot {
  balls   : (Element | null)[]
  band    : (Element | null)[]
  columns : aggregateColumns.Column[]
  open    : number | null
  popped  : (Element | null)[][]
  random  : Estimate
  seeds   : readonly number[]
  still   : boolean
  toggle  : (seed: number) => void
}

/**
 * The classes and the style of a part gliding to its place on the travel
 * curve, landing at once under reduced motion.
 */
const GLIDES = {
  classes : 'transition-transform ease-travel motion-reduce:transition-none',
  style   : { transitionDuration: `${aggregateColumns.MOVE.glide}ms` }
} as const
/**
 * The plot's heights in pixels: the line of each column's interval, the foot
 * of its scale, the line of each column's name, of its share, and of its
 * start, its top, the whole plot, and how far each of an interval's two lines
 * sits from its own line where a column is too narrow to set it on one.
 */
const HEIGHT = {
  bounds : 220,
  foot   : 140,
  name   : 162,
  share  : 202,
  start  : 176,
  top    : 16,
  whole  : 226,
  wrap   : 6
} as const
/**
 * The size of one of the Poké Ball's pixels in the plot, at a group's
 * interquartile mean and at each of its runs.
 */
const PIXEL = { mean: 1.75, run: 1 } as const
/**
 * The shares the plot's scale marks.
 */
const SCALE = [0, 0.5, 1] as const
/**
 * The plot's widths in pixels: the room between two runs a column opens out
 * side by side, the room its scale's values take at its left, the shortest
 * area a press on a run lands in, and the narrowest column that sets its
 * interval on one line.
 */
export const WIDTH = { gap: 4, scale: 40, target: 24, wide: 76 } as const
/**
 * The style delaying each seed's run as a column opens out, set once.
 */
const staggers = committedSeeds.map((_, n) => ({
  transitionDelay    : `${n * aggregateColumns.MOVE.stagger}ms`,
  transitionDuration : `${aggregateColumns.MOVE.open}ms`
}))

/**
 * Sets a share as its numeral in whole points, counting along from the share
 * it last set over one glide, at once under reduced motion.
 */
const Points = defineComponent({
  name  : 'Points',
  props : { share: { required: true, type: Number }, still: { required: true, type: Boolean } },
  setup : props => {
    const shown = aggregateColumns.useEased(() => props.share, () => props.still)
    return () => aggregateColumns.numerals[shown.value]
  }
})

/**
 * Reads the style moving a part drawn at the top of the plot down to `y`,
 * gliding there.
 */
const at = (y: number) => ({ ...GLIDES.style, transform: `translateY(${y}px)` })

/**
 * Draws the interval from `from` to `to` under the column standing at `x`,
 * on one line where `wide` holds and on two otherwise, its figures counting
 * along with the means.
 */
function drawBounds(from: number, to: number, still: boolean, wide: boolean, x: number): VNode {
  return (
    <text class={TICK} text-anchor="middle" x={x} y={wide ? HEIGHT.bounds : HEIGHT.bounds - HEIGHT.wrap}>
      {wide
        ? <>{'['}<Points share={from} still={still} />{', '}<Points share={to} still={still} />{']'}</>
        : <>
          <tspan x={x} y={HEIGHT.bounds - HEIGHT.wrap}>{'['}<Points share={from} still={still} />{','}</tspan>
          <tspan x={x} y={HEIGHT.bounds + HEIGHT.wrap}><Points share={to} still={still} />{']'}</tspan>
        </>}
    </text>
  )
}

/**
 * Draws one column's group at the place `place` gives it: its interval and
 * its Poké Ball gliding to their places, hidden while its runs stand open
 * beside it, each of its runs, its name, its start, and its figures, setting
 * its ball's element in `balls` at `n`.
 */
function drawColumn(
  { each, estimate, runs } : aggregateColumns.Column,
  balls                    : (Element | null)[],
  n                        : number,
  place                    : Place
): VNode {
  const [from, to] = aggregate.spanOf(estimate)
  const { x }      = place
  const ball       = ballSide * PIXEL.mean
  const bar        = { class: ['fill-current', GLIDES.classes], width: ball + 6, x: x - ball / 2 - 3, y: 0 }
  const hue        = HUES[each.group.hue]
  const label      = [hue.text, 'fill-current font-code text-label tracking-caps uppercase']
  const shut       = place.open ? 'opacity-0' : 'opacity-100'
  return (
    <g class={hue.ink}>
      <g class={['transition-opacity motion-reduce:transition-none', shut]}>
        <g class="opacity-15">
          <rect {...bar} height={ball} rx={ball / 2} style={at(yOf(to) - ball / 2)} />
          <rect {...bar} height={1} style={stretch(yOf(to), yOf(from))} />
          <rect {...bar} height={ball} rx={ball / 2} style={at(yOf(from) - ball / 2)} />
        </g>
        <g class={GLIDES.classes} style={at(yOf(estimate.value) - ball / 2)}>
          <g class="origin-bottom transform-fill" ref={(el: unknown) => { balls[n] = el as Element | null }}>
            {drawBall(PIXEL.mean, x - ball / 2)}
          </g>
        </g>
      </g>
      {drawRuns(runs, estimate.value, n, place)}
      <text class={[label, 'font-semibold']} text-anchor="middle" x={x} y={HEIGHT.name}>
        {AGENTS[each.group.agent].short}
      </text>
      <text class={label} text-anchor="middle" x={x} y={HEIGHT.start}>
        {each.group.curriculum ? 'Curr.' : 'Bedroom'}
      </text>
      <text
        class="fill-ink font-code text-small font-medium tabular-nums"
        text-anchor="middle"
        x={x}
        y={HEIGHT.share}
      >
        <Points share={estimate.value} still={place.still} />{'%'}
      </text>
      {estimate.interval ? drawBounds(from, to, place.still, place.step >= WIDTH.wide, x) : null}
    </g>
  )
}

/**
 * Draws random presses' band and line across a plot `width` wide and its
 * figures above them, each gliding to its place and settling there, setting
 * the element that settles in `band`.
 */
function drawRandom(random: Estimate, band: (Element | null)[], still: boolean, width: number): VNode {
  const [low, high] = aggregate.spanOf(random)
  return (
    <g class="text-random" ref={(el: unknown) => { band[0] = el as Element | null }}>
      <rect
        class={['fill-current opacity-15', GLIDES.classes]}
        height={1}
        style={stretch(yOf(high), yOf(low))}
        width={width - WIDTH.scale}
        x={WIDTH.scale}
        y={0}
      />
      <path
        class={['stroke-current', GLIDES.classes]}
        d={`M${WIDTH.scale},0H${width}`}
        stroke-width={IDENTITY.lengths.strokes.line}
        style={at(yOf(random.value))}
      />
      <g class={GLIDES.classes} style={at(yOf(high) - 6)}>
        <text
          class="fill-seacaller-text font-code text-label font-semibold tracking-caps tabular-nums uppercase"
          text-anchor="end"
          x={width - 4}
          y={0}
        >
          {'Random presses '}<Points share={random.value} still={still} />{'%'}
          {random.interval
            ? <>{' ['}<Points share={low} still={still} />{', '}<Points share={high} still={still} />{']'}</>
            : null}
        </text>
      </g>
    </g>
  )
}

/**
 * Draws a column's runs, gathered behind its Poké Ball at `mean` while the
 * column is shut and opening out side by side to each run's share, a half
 * beat apart, while it is open, a run whose seed is left out drawn empty and
 * a press anywhere in its share of the column switching its seed, setting
 * each run's Poké Ball in `place.popped` at the column's place `n`.
 */
function drawRuns(runs: readonly aggregate.Paired[], mean: number, n: number, place: Place): VNode[] {
  const spread = aggregateColumns.spreadOf(runs.length, WIDTH.gap, ballSide * PIXEL.run, place.step)
  const pixel  = PIXEL.run * spread.scale
  const small  = ballSide * pixel
  const tall   = Math.max(small + 8, WIDTH.target)
  const shown  = place.open ? 'pointer-events-auto cursor-pointer opacity-100' : 'opacity-0'
  const set    = (run: aggregate.Paired) => (el: unknown) => {
    place.popped[committedSeeds.indexOf(run.seed)]![n] = el as Element | null
  }
  return runs.map((run, k) => (
    <g
      class={['transition motion-reduce:transition-none', shown]}
      onClick={() => place.toggle(run.seed)}
      style={{
        ...staggers[k],
        transform: place.open
          ? `translate(${spread.offsets[k]}px, ${yOf(run.share) - small / 2}px)`
          : `translate(0px, ${yOf(mean) - small / 2}px)`
      }}
    >
      <rect
        class="fill-transparent"
        height={tall}
        width={spread.pitch}
        x={place.x - spread.pitch / 2}
        y={(small - tall) / 2}
      />
      <g class="origin-center transform-fill" ref={set(run)}>
        {drawBall(pixel, place.x - small / 2, !place.seeds.includes(run.seed))}
      </g>
    </g>
  ))
}

/**
 * Reads the style stretching a part one pixel tall, drawn at the top of the
 * plot, from `top` down to `bottom`, gliding there.
 */
const stretch = (top: number, bottom: number) =>
  ({ ...GLIDES.style, transform: `translateY(${top}px) scaleY(${Math.max(bottom - top, 0)})` })

/**
 * Reads the height in the plot of `share`.
 */
const yOf = (share: number) => HEIGHT.foot - share * (HEIGHT.foot - HEIGHT.top)

/**
 * Draws the plot `width` wide: its scale, random presses' band, and each
 * column at its share of the width, setting each settling part's element in
 * the lists `plot` holds.
 */
export function drawPlot(plot: Plot, width: number): VNode {
  const step = (width - WIDTH.scale) / plot.columns.length
  return (
    <svg {...SVG} shape-rendering="geometricPrecision" viewBox={`0 0 ${width} ${HEIGHT.whole}`}>
      {drawAxis(SCALE.map(share => `M${WIDTH.scale},${yOf(share)}H${width}`).join(''))}
      {SCALE.map(share => (
        <text class={TICK} dominant-baseline="middle" text-anchor="end" x={WIDTH.scale - 6} y={yOf(share)}>
          {`${share * 100}%`}
        </text>
      ))}
      {drawRandom(plot.random, plot.band, plot.still, width)}
      {plot.columns.map((column, n) => drawColumn(column, plot.balls, n, {
        ...plot,
        open : plot.open === n,
        step : step,
        x    : WIDTH.scale + step * (n + 0.5)
      }))}
    </svg>
  )
}
