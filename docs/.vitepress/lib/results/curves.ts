import { useElementVisibility, useTransition }              from '@vueuse/core'
import { type ComputedRef, type Ref, computed, ref, watch } from 'vue'

import { type Frame, type PlotLabel, frameOf, multiplesOf, round } from '../drawing/plot.ts'
import { IDENTITY }                                                from '../identity/identity.ts'
import { BEAT, TRAVEL, useMotion }                                 from '../widgets/motion.ts'
import { useDrawnWidth }                                           from '../widgets/width.ts'
import { COMMITTED, type Group, type Results, type Score, groupsOf, meansOf } from './results.ts'
import { useToggles }                                              from './toggles.ts'

/**
 * One group's curve laid out: the group, whether its line is dashed for the
 * curriculum, its path, and the point of each evaluation its glyph marks.
 */
export interface Curve {
  dashed : boolean
  d      : string
  group  : Group
  points : readonly (readonly [number, number])[]
}

/**
 * The learning curves laid out in a plot: the width a line's clip opens across
 * in full, the height of random presses' level line, the plot's frame, the
 * gridlines at each labeled share, the labels along both axes, each group's
 * curve, and the title of each axis.
 */
export interface Curves {
  across   : number
  baseline : number
  frame    : Frame
  grid     : string
  labels   : readonly PlotLabel[]
  lines    : readonly Curve[]
  titles   : readonly PlotLabel[]
}

/**
 * The plot's height, the room it leaves on each side, its right side wide
 * enough for the glyph a curve ends on, the shares and the steps it labels,
 * and the title of each axis, both stating the variable and its unit.
 */
export const PLOTTING = {
  drop   : 20,
  every  : 500_000,
  gap    : IDENTITY.lengths.spacing['2'],
  height : IDENTITY.lengths.sizes['results-plot'],
  shares : [0, 0.25, 0.5, 0.75, 1],
  title  : IDENTITY.lengths.spacing['5'],
  titles : {
    reached : 'Episodes reaching the goal (%)',
    steps   : 'Environment steps (millions)'
  },
  box    : {
    bottom : IDENTITY.lengths.spacing['7'],
    left   : IDENTITY.lengths.spacing['7'],
    right  : IDENTITY.lengths.spacing['4'],
    top    : IDENTITY.lengths.spacing['3']
  }
} as const

/**
 * Lays out the curve of each of `groups` at `height` by `width` pixels, the
 * interquartile mean across its runs' shares reaching the goal at each
 * evaluation, random presses' share `random` as a level line, and the steps
 * along the bottom up to the evaluation read last, labeled in millions every
 * half million.
 */
export function curvesOf(groups: readonly Group[], random: number, height: number, width: number): Curves {
  const frame  = frameOf({ ...PLOTTING.box, top: PLOTTING.box.top + PLOTTING.title }, height, width)
  const means  = groups.map(group => meansOf(group))
  const last   = Math.max(...means.flatMap(scores => scores.map(score => score.step)))
  const point  = (score: Omit<Score, 'argmax'>) => [frame.x(score.step, last), frame.y(score.reached, 1)] as const
  const left   = frame.x(0, 1)
  const steps  = multiplesOf(PLOTTING.every, last)
  const middle = round((left + frame.end) / 2)

  return {
    across   : frame.end - left + PLOTTING.box.right + PLOTTING.gap,
    baseline : frame.y(random, 1),
    frame    : frame,
    grid     : PLOTTING.shares.map(share => `M${left},${frame.y(share, 1)}H${frame.end}`).join(''),
    labels   : [
      ...PLOTTING.shares.map(share => ({
        anchor : 'end' as const,
        text   : `${share * 100}%`,
        x      : left - PLOTTING.gap,
        y      : frame.y(share, 1) + PLOTTING.gap / 2
      })),
      ...steps.map(step => ({
        anchor : step === 0 ? 'start' as const : 'middle' as const,
        text   : String(step / 1_000_000),
        x      : frame.x(step, last),
        y      : frame.floor + PLOTTING.drop
      }))
    ],
    lines : groups.map((group, n) => {
      const points = means[n]!.map(score => point(score))
      return { dashed: group.curriculum, d: `M${points.join('L')}`, group, points }
    }),
    titles : [
      { anchor: 'middle', text: PLOTTING.titles.steps, x: middle, y: frame.floor + 2 * PLOTTING.drop },
      { anchor: 'start', text: PLOTTING.titles.reached, x: 0, y: PLOTTING.box.top + PLOTTING.gap }
    ]
  }
}

/**
 * Traces each of `groups` out along the steps while `pressed` holds it and
 * draws it back once released, the share of its line shown easing over two
 * glides out and one back. The groups pressed at first wait until `seen`
 * holds, then trace out a beat apart, and every line stands whole at once
 * under reduced motion.
 */
function useTraces(groups: readonly Group[], pressed: Ref<ReadonlySet<string>>, seen: Ref<boolean>): ComputedRef<number>[] {
  const motion = useMotion()
  const first  = ref(true)
  const order  = [...pressed.value]
  watch(pressed, () => { first.value = false })

  return groups.map(group => {
    const shown = computed(() => pressed.value.has(group.id) && (seen.value || !motion.value))
    return useTransition(() => shown.value ? 1 : 0, {
      delay    : computed(() => first.value ? Math.max(0, order.indexOf(group.id)) * BEAT : 0),
      disabled : computed(() => !motion.value),
      duration : computed(() => (shown.value ? 4 : 2) * BEAT),
      easing   : TRAVEL
    })
  })
}

/**
 * Draws the learning curves of the runs `results` holds, the committed runs
 * unless given others, in `box`, measuring the width they take there and
 * tracing each group's curve out once `box` first comes into view.
 *
 * Returns:
 *   The curves laid out, the groups, random presses' share across every seed,
 *   the toggles pressing each group, how far each group's curve has traced
 *   out, and the width drawn at.
 */
export function useCurves(box: Ref<HTMLElement | undefined>, results: Results = COMMITTED) {
  const groups  = groupsOf(results)
  const random  = results.random
  const width   = useDrawnWidth(box, 240)
  const seen    = useElementVisibility(box, { once: true })
  const toggles = useToggles(groups)
  const traces  = useTraces(groups, toggles.pressed, seen)

  return {
    curves  : computed(() => curvesOf(groups, random?.value ?? 0, PLOTTING.height, width.value)),
    groups  : groups,
    random  : random,
    toggles : toggles,
    traces  : traces,
    width   : width
  }
}
