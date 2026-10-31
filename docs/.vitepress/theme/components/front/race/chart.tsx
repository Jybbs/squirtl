import * as chart             from '../../../../lib/front/race/chart.ts'
import { RACERS, type Racer } from '../../../../lib/front/race.ts'
import { counted }            from '../../../../lib/widgets/numbers.ts'
import * as clock             from '../../kit/clock.tsx'
import { ROLES }              from '../../kit/hues.ts'
import * as plots             from '../../kit/plots.tsx'

/**
 * Draws the axes of `plot`: the gridlines and their counts, the steps, the
 * title, and the dashed line at the episode's limit.
 */
function drawAxes(plot: chart.RacePlot) {
  const { dash, strokes } = chart.CHART

  return [
    plots.drawAxis(plot.grid),
    ...[...plot.counts, ...plot.steps].map(label => plots.drawLabel(label)),
    plots.drawLabel(plot.title, plots.TITLE),
    <line
      class="stroke-quiet"
      stroke-dasharray={`${dash} ${dash}`}
      stroke-width={strokes.reference}
      x1={plot.limit}
      x2={plot.limit}
      y1={plot.top}
      y2={plot.floor}
    />
  ]
}

/**
 * Draws the clock of `plot` at `mark`: its line, a dot on each player's curve
 * where it stands, and its chip naming the step it reads.
 */
function drawClock(plot: chart.RacePlot, mark: chart.StopMark) {
  const { chip, dot, overhang, strokes } = chart.CHART

  return [
    clock.drawClockLine(plot.floor, plot.top - overhang, mark.x),
    ...RACERS.map(racer => (
      <circle
        class={['stroke-ground', ROLES[racer].fill]}
        cx={mark.x}
        cy={mark.dots[racer]}
        key={racer}
        r={dot}
        stroke-width={strokes.line}
      />
    )),
    clock.drawClockChip(mark.chip, counted(mark.now, 'step'), chip)
  ]
}

/**
 * Draws `plot` with the clock at its stop `stop`, filling the box it sits in:
 * its axes, each player's whole curve faint and the part the clock has passed
 * in its hue through the clip `clip` names, and the clock.
 */
export function drawRace(plot: chart.RacePlot, clip: string, stop: number) {
  const mark  = plot.stops[stop]!
  const curve = (racer: Racer, faint: boolean) => (
    <path
      class={['fill-none', faint && 'opacity-25', ROLES[racer].stroke]}
      d={plot.curves[racer]}
      key={racer}
      {...plots.CURVE}
    />
  )

  return (
    <svg {...plots.SVG} viewBox={`0 0 ${plot.width} ${plot.height}`}>
      {clock.drawReveal(plot.height, clip, mark.x + chart.CHART.strokes.line)}
      {drawAxes(plot)}
      {RACERS.map(racer => curve(racer, true))}
      <g clip-path={`url(#${clip})`}>{RACERS.map(racer => curve(racer, false))}</g>
      {drawClock(plot, mark)}
    </svg>
  )
}
