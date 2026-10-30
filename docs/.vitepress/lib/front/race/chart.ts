import { type MaybeElementRef, clamp }               from '@vueuse/core'
import { type ComputedRef, type Ref, computed, ref } from 'vue'

import * as plot                   from '../../drawing/plot.ts'
import { EPISODE }                 from '../../game/episode.ts'
import { IDENTITY }                from '../../identity/identity.ts'
import { count }                   from '../../widgets/numbers.ts'
import { type Playback, useScrub } from '../../widgets/scrub.ts'
import { useDrawnWidth }           from '../../widgets/width.ts'
import * as race                   from '../race.ts'

/**
 * The tuning of the race's chart, each length in the pixels its view box
 * counts:
 *
 * - `box`, the room each side of the curves leaves for the chip and the labels
 * - `chip`, the width of the clock's chip, and `slack`, how far past the
 *   curves' left edge it may sit
 * - `dash`, the length of a dash and a gap of the limit's line
 * - `dot`, the radius of the dot each curve takes at the clock
 * - `every`, the episodes between two gridlines
 * - `height`, the chart's height, which its box takes in the sheet as well
 * - `label`, the gap of a count's label from the curves, the shift of its
 *   baseline below its gridline, and the drops of a step's label and of the
 *   title below the floor
 * - `least`, the smallest width the chart draws at
 * - `near`, the room a step's label needs before the limit's label
 * - `overhang`, how far the clock's line reaches above the curves
 * - `strokes`, the identity's stroke widths
 */
export interface Chart {
  box      : plot.Sides
  chip     : number
  dash     : number
  dot      : number
  every    : number
  height   : number
  label    : plot.Labeling & { title: number }
  least    : number
  near     : number
  overhang : number
  slack    : number
  strokes  : plot.Strokes
}

/**
 * The race drawn at one width: its gridlines and the labels of their counts,
 * the floor and the top of its curves, the labels of its steps and its title,
 * the dashed line at the episode's limit, each player's curve, and where the
 * clock stands at each of its stops.
 */
export interface RacePlot {
  counts : readonly plot.PlotLabel[]
  curves : Readonly<Record<race.Racer, string>>
  floor  : number
  grid   : string
  height : number
  limit  : number
  steps  : readonly plot.PlotLabel[]
  stops  : readonly StopMark[]
  title  : plot.PlotLabel
  top    : number
  width  : number
}

/**
 * The chart laid out at one width: the right edge of its curves, its floor, its
 * width, and the point of a step and of a count of episodes reached.
 */
interface Scale extends Pick<plot.Frame, 'end' | 'floor'> {
  width : number
  x     : (step: number) => number
  y     : (reached: number) => number
}

/**
 * Where the clock stands at one stop: the step it reads, the left of its line
 * and of its chip, and the height of each player's dot on its curve.
 */
export interface StopMark {
  chip : number
  dots : Readonly<Record<race.Racer, number>>
  now  : number
  x    : number
}

/**
 * The chart's tuning, its sides and its chip's slack read from the identity's
 * spacing and its height from the identity's sizes.
 */
export const CHART: Chart = {
  chip     : 104,
  dash     : 3,
  dot      : 5,
  every    : 10,
  height   : IDENTITY.lengths.sizes['race-plot'],
  label    : { ...plot.LABELING, title: 42 },
  least    : 240,
  near     : 140,
  overhang : 4,
  slack    : IDENTITY.lengths.spacing['2'],
  strokes  : IDENTITY.lengths.strokes,
  box      : {
    bottom : IDENTITY.lengths.spacing['7'],
    left   : IDENTITY.lengths.spacing['6'],
    right  : IDENTITY.lengths.spacing['2'],
    top    : IDENTITY.lengths.spacing['6']
  }
}

/**
 * The pace the clock runs at across its stops, in milliseconds a stop, and how
 * long it rests at the episode's limit before it runs again.
 */
const CLOCK_TEMPO = { beat: 50, rest: 5000 }

/**
 * The name a screen reader reads for the step clock along the chart.
 */
const SLIDER = 'The step clock along the chart, which sets how far every episode has run'

/**
 * Draws the curve of the episodes of `outcomes` that had reached the starter by
 * each step on `scale`, rising one episode at the step each reached it and
 * running on to the episode's limit.
 */
function curveOf(outcomes: readonly race.Ending[], scale: Scale): string {
  const { x, y } = scale
  return outcomes.filter(each => each.reached)
    .map(each => each.steps)
    .toSorted((a, b) => a - b)
    .reduce((d, steps, n) => `${d}H${x(steps)}V${y(n + 1)}`, `M${x(1)},${y(0)}`) + `H${x(EPISODE.limit)}`
}

/**
 * Labels the steps on `scale`, each power of ten below the episode's limit and
 * then the limit, leaving out a step's label where it would meet the limit's.
 */
function labeledSteps(scale: Scale, tuning: Chart): plot.PlotLabel[] {
  const { x } = scale
  const below = Array.from({ length: Math.ceil(Math.log10(EPISODE.limit)) }, (_, power) => 10 ** power)
  return [...below, EPISODE.limit]
    .filter(step => step === EPISODE.limit || x(EPISODE.limit) - x(step) >= tuning.near)
    .map(step => ({
      anchor : step === EPISODE.limit ? 'end' : step === 1 ? 'start' : 'middle',
      text   : step === EPISODE.limit ? `${count(step)}, the limit` : count(step),
      x      : x(step),
      y      : scale.floor + tuning.label.drop
    }))
}

/**
 * Reads one figure of each player of the race through `read`.
 */
const perRacer = <T>(read: (racer: race.Racer) => T): Record<race.Racer, T> =>
  Object.fromEntries(race.RACERS.map(racer => [racer, read(racer)])) as Record<race.Racer, T>

/**
 * Lays out the chart at `width` pixels, its floor and its curves' right edge,
 * and the point of a step along the log scale from the first step to the
 * episode's limit and of a count of the episodes reached.
 */
function scaleOf(evaluating: race.Evaluating, tuning: Chart, width: number): Scale {
  const frame = plot.frameOf(tuning.box, tuning.height, width)
  const span  = Math.log10(EPISODE.limit)

  return {
    end   : frame.end,
    floor : frame.floor,
    width : width,
    x     : step => frame.x(Math.log10(step), span),
    y     : reached => frame.y(reached, evaluating.episodes)
  }
}

/**
 * Marks where the clock stands on `scale` at each of its stops, its chip kept
 * inside the chart, and the height of each player's dot.
 */
function stopsOf(
  drawn      : race.Race,
  evaluating : race.Evaluating,
  scale      : Scale,
  tuning     : Chart
): StopMark[] {
  const { box, chip, slack } = tuning
  return Array.from({ length: evaluating.stops + 1 }, (_, stop) => {
    const now = race.clockAt(stop, evaluating)
    const at  = scale.x(now)
    return {
      chip : plot.round(clamp(at - chip / 2, box.left - slack, scale.width - chip)),
      dots : perRacer(racer => scale.y(race.reachedBy(drawn[racer], now))),
      now  : now,
      x    : at
    }
  })
}

/**
 * Draws `drawn` at `width` pixels: a gridline every `every` episodes, each
 * labeled with its count, the labeled steps, each player's curve of the
 * episodes that had reached the starter by each step, and where the clock
 * stands at each of its stops.
 */
export function racePlotOf(
  drawn      : race.Race,
  width      : number,
  evaluating : race.Evaluating = race.EVALUATING,
  tuning     : Chart           = CHART
): RacePlot {
  const { box, label } = tuning
  const scale          = scaleOf(evaluating, tuning, width)
  const counts         = plot.multiplesOf(tuning.every, evaluating.episodes)

  return {
    curves : perRacer(racer => curveOf(drawn[racer], scale)),
    floor  : scale.floor,
    grid   : counts.map(each => `M${box.left},${scale.y(each)}H${scale.end}`).join(''),
    height : tuning.height,
    limit  : scale.x(EPISODE.limit),
    steps  : labeledSteps(scale, tuning),
    stops  : stopsOf(drawn, evaluating, scale, tuning),
    title  : { anchor: 'start', text: 'Steps, on a log scale', x: box.left, y: scale.floor + label.title },
    top    : box.top,
    width  : width,
    counts : counts.map(each => ({
      anchor : 'end',
      text   : String(each),
      x      : box.left - label.gap,
      y      : scale.y(each) + label.baseline
    }))
  }
}

/**
 * Measures the chart's box `box` and draws `drawn` at its width under `tuning`,
 * no narrower than the least the chart takes.
 */
export function useRace(
  box    : Ref<HTMLElement | undefined>,
  drawn  : race.Race,
  tuning : Chart = CHART
): ComputedRef<RacePlot> {
  const width = useDrawnWidth(box, tuning.least)
  return computed(() => racePlotOf(drawn, width.value, race.EVALUATING, tuning))
}

/**
 * Runs the clock across its stops of the race `drawn` while the widget at
 * `root` shows on screen, resting at the episode's limit before it runs again,
 * and makes the chart the slider over it, which sets how far every episode has
 * run.
 */
export function useRaceClock(drawn: race.Race, root: MaybeElementRef): Playback {
  const at    = ref(0)
  const stops = race.EVALUATING.stops

  const scrub = useScrub(root, {
    beat    : CLOCK_TEMPO.beat,
    done    : () => at.value >= stops,
    finish  : () => { at.value = stops },
    rest    : CLOCK_TEMPO.rest,
    restart : () => { at.value = 0 },
    tick    : () => { at.value += 1 }
  }, {
    at       : at,
    count    : stops + 1,
    describe : stop => race.describeStop(drawn, stop),
    label    : SLIDER,
    seek     : stop => { at.value = stop }
  })

  return { at, scrub }
}
