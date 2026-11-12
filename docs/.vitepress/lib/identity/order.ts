import { clamp }                                    from '@vueuse/core'
import { type Ref, computed, reactive, ref, watch } from 'vue'

import { useSwitches }                  from '../widgets/choice.ts'
import { useFrameLoop }                 from '../widgets/frames.ts'
import { useMotion }                    from '../widgets/motion.ts'
import { useDrawnWidth }                from '../widgets/width.ts'
import { type Hue, IDENTITY, type Role } from './identity.ts'
import { namedOf }                      from './palette.ts'

/**
 * One made-up run the series order draws, the hue it takes, its place in the
 * identity's `order`, the role that hue carries, and its value at each step.
 */
export interface Run {
  hue    : Hue
  place  : number
  role   : Role
  values : readonly number[]
}

/**
 * A point of a line, its left and its top.
 */
export type Point = readonly [number, number]

/**
 * The margins a chart leaves around its lines.
 */
interface Margins {
  bottom : number
  left   : number
  right  : number
  top    : number
}

/**
 * Where the pen stands, how much of each line it has drawn from 0 to 1, the
 * line it is drawing or rewinding, and whether it is rewinding every line
 * before it draws them again.
 */
interface Pen {
  active    : Hue | null
  drawn     : Record<Hue, number>
  rewinding : boolean
}

/**
 * The steps each made-up run takes a value at.
 */
export const STEPS = 26

/**
 * How long the pen takes to draw one line on and to rewind it, in
 * milliseconds.
 */
export const TEMPO = { draw: 620, rewind: 240 }

/**
 * The words naming each role a switch reads.
 */
export const ROLE_WORDS: Readonly<Record<Role, string>> = {
  agent     : 'The agent',
  milestone : 'Milestones',
  novelty   : 'New positions',
  random    : 'Random presses',
  starter   : 'The starter'
}

/**
 * The shape each role's made-up run takes across the steps from 0 to 1, the
 * agent's rising late and steeply, the milestones' in a staircase, the new
 * positions' early and flattening, random presses' level, and the starter's
 * late.
 */
const SHAPES: Readonly<Record<Role, (x: number) => number>> = {
  agent     : x => 0.06 + 0.74 / (1 + Math.exp(-9 * (x - 0.45))),
  milestone : x => 0.04 + 0.56 * Math.min(1, Math.floor(x * 5.2) / 4) + 0.02 * x,
  novelty   : x => 0.08 + 0.8 * (1 - Math.exp(-x * 4.2)),
  random    : x => 0.12 + 0.015 * Math.sin(x * 23),
  starter   : x => 0.02 + 0.4 / (1 + Math.exp(-14 * (x - 0.72)))
}

/**
 * The role each series hue carries, the reverse of the identity's `roles`.
 */
const ROLE_OF = Object.fromEntries(Object.entries(IDENTITY.roles).map(([role, hue]) => [hue, role])) as Record<Hue, Role>

/**
 * One made-up run for each series hue, in the identity's `order`.
 */
export const RUNS: readonly Run[] = (IDENTITY.order as Hue[]).map((hue, place) => ({
  hue,
  place,
  role   : ROLE_OF[hue],
  values : Array.from({ length: STEPS }, (_, n) => SHAPES[ROLE_OF[hue]](n / (STEPS - 1)))
}))

/**
 * Names `run` by its place in the order and its hue, as a switch tags it.
 */
export function tagOf(run: Run): string {
  return `${run.place + 1} · ${namedOf(IDENTITY.hues[run.hue].token).name}`
}

/**
 * Makes a pen with every line drawn whole where `whole` is set and none drawn
 * otherwise.
 */
export function penOf(whole: boolean): Pen {
  return { active: null, drawn: Object.fromEntries(RUNS.map(run => [run.hue, whole ? 1 : 0])) as Record<Hue, number>, rewinding: false }
}

/**
 * Moves `pen` on by `elapsed` milliseconds with the lines `shown` shown: every
 * line hidden rewinds, and the pen rewinds the last line drawn while it is
 * rewinding, then draws the first line shown that is not yet whole, each line
 * in the order the identity takes them.
 *
 * Returns:
 *   Whether any line moved.
 */
export function advance(pen: Pen, shown: ReadonlySet<Hue>, elapsed: number): boolean {
  const step = (hue: Hue, by: number) => { pen.drawn[hue] = clamp(pen.drawn[hue] + by, 0, 1) }
  const hidden = RUNS.filter(run => !shown.has(run.hue) && pen.drawn[run.hue] > 0)
  for (const run of hidden) step(run.hue, -elapsed / TEMPO.rewind)
  pen.active = null
  if (pen.rewinding) {
    const last = RUNS.findLast(run => shown.has(run.hue) && pen.drawn[run.hue] > 0)
    if (last) {
      step(last.hue, -elapsed / TEMPO.rewind)
      pen.active = last.hue
    }
    else pen.rewinding = false
  }
  if (!pen.rewinding) {
    const next = RUNS.find(run => shown.has(run.hue) && pen.drawn[run.hue] < 1)
    if (next) {
      step(next.hue, elapsed / TEMPO.draw)
      pen.active = next.hue
    }
  }
  return hidden.length > 0 || pen.active !== null
}

/**
 * Sets every line of `pen` where it ends, each line `shown` whole and every
 * other none.
 */
export function finish(pen: Pen, shown: ReadonlySet<Hue>): void {
  for (const run of RUNS) pen.drawn[run.hue] = shown.has(run.hue) ? 1 : 0
  pen.active    = null
  pen.rewinding = false
}

/**
 * Finds the point `share` of the way along the line through `points`, measured
 * along its length, as a dash drawn on a path of length 1 reaches it.
 */
export function pointAt(points: readonly Point[], share: number): Point {
  const lengths = points.slice(1).map(([x, y], n) => Math.hypot(x - points[n]![0], y - points[n]![1]))
  let left      = share * lengths.reduce((sum, each) => sum + each, 0)
  for (const [n, length] of lengths.entries()) {
    if (left <= length) {
      const [[x0, y0], [x1, y1]] = [points[n]!, points[n + 1]!]
      const t                    = length === 0 ? 0 : left / length
      return [x0 + (x1 - x0) * t, y0 + (y1 - y0) * t]
    }
    left -= length
  }
  return points.at(-1)!
}

/**
 * The plate's margins around its lines, room for the figures at the left and
 * along the foot, and the share of its width it stands tall, held between its
 * least and greatest height.
 */
export const PLATE = { bottom: 26, high: 260, left: 40, low: 150, right: 14, tall: 0.42, top: 14 }

/**
 * Places the value `value` from 0 to 1 up a chart `height` tall inside
 * `margins`, as the top of its point.
 */
export function yOf(value: number, height: number, margins: Margins): number {
  return margins.top + (1 - value) * (height - margins.top - margins.bottom)
}

/**
 * Places the values of `run` along a chart `width` by `height` inside
 * `margins`.
 */
export function pointsOf(run: Run, width: number, height: number, margins: Margins): Point[] {
  return run.values.map((value, n) => [margins.left + n / (STEPS - 1) * (width - margins.left - margins.right), yOf(value, height, margins)])
}

/**
 * Writes `points` as an SVG path through each.
 */
export function pathOf(points: readonly Point[]): string {
  return points.map(([x, y], n) => `${n === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join('')
}

/**
 * Draws every made-up run on a plate the width it takes in `box`, a pen
 * drawing each line on while the plate shows and motion plays, and every line
 * standing whole at once under reduced motion. A reader's switch shows or
 * hides a line, the pen rewinding a line hidden, and `again` rewinds every
 * line from wherever the pen stands before it draws them on again.
 *
 * Returns:
 *   The plate's width and height, each line's points beside its run, the pen,
 *   the switches over the lines, and the call that draws them again.
 */
export function usePen(box: Ref<HTMLElement | undefined>) {
  const width    = useDrawnWidth(box, 240)
  const height   = computed(() => Math.round(clamp(width.value * PLATE.tall, PLATE.low, PLATE.high)))
  const motion   = useMotion()
  const hues     = RUNS.map(run => run.hue)
  const shown    = ref<ReadonlySet<Hue>>(new Set(hues))
  const pen      = reactive(penOf(!motion.value))
  const wake     = useFrameLoop(box, elapsed => advance(pen, shown.value, elapsed))
  const go       = () => motion.value ? wake() : finish(pen, shown.value)

  watch([shown, motion], go)

  return {
    again    : () => {
      pen.rewinding = true
      go()
    },
    height   : height,
    lines    : computed(() => RUNS.map(run => ({ points: pointsOf(run, width.value, height.value, PLATE), run }))),
    pen      : pen,
    switches : useSwitches(hues, shown),
    width    : width
  }
}
