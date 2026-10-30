import { type MaybeElementRef, useElementSize } from '@vueuse/core'
import { type ComputedRef, computed }           from 'vue'

import * as plot        from '../../drawing/plot.ts'
import { IDENTITY }     from '../../identity/identity.ts'
import * as numbers     from '../../widgets/numbers.ts'
import type * as reward from '../reward.ts'

/**
 * The tuning of the return's climb, each length in the pixels its view box
 * counts:
 *
 * - `box`, the room each side of the climb leaves for its labels
 * - `dot`, `halo`, and `head`, the radii of a jump's dot and of the step shown
 * - `every`, the steps between two step labels at each width
 * - `label`, the drop of a step label below the floor, the gap of a value
 *   label from the axis, and the shift of its baseline below its value
 * - `least`, the smallest width and height the climb draws at
 * - `narrow`, the width below which the step labels thin out
 * - `reach`, how far past the step shown the course reveals
 * - `rise`, how far the axis runs above the climb's top
 * - `rug`, the height of a new position's tick along the floor
 * - `strokes`, the identity's stroke widths
 * - `tick` and `ticks`, the length of a value's tick and the values it marks
 * - `tile`, the side of a sprite's frame drawn on a jump's tile, the gap from
 *   the tile to the jump's dot, the tile's corner, and its side
 * - `title`, the room the axis's title takes at its end
 * - `top`, the return the climb's top stands for
 */
export interface Climb {
  box     : plot.Sides
  dot     : number
  every   : { narrow: number, wide: number }
  halo    : number
  head    : number
  label   : plot.Labeling
  least   : { height: number, width: number }
  narrow  : number
  reach   : number
  rise    : number
  rug     : number
  strokes : plot.Strokes
  tick    : number
  ticks   : readonly number[]
  tile    : { art: number, gap: number, radius: number, side: number }
  title   : number
  top     : number
}

/**
 * The climb drawn at one width and height: the path of its axis with each
 * value's tick, the course of the return, the point each step stands at, each
 * jump's mark, the tick of each new position, and its labels.
 */
export interface ClimbPlot {
  axis   : string
  course : string
  heads  : readonly ClimbPoint[]
  height : number
  jumps  : readonly JumpMark[]
  rug    : string
  steps  : readonly plot.PlotLabel[]
  title  : plot.PlotLabel
  values : readonly plot.PlotLabel[]
  width  : number
}

/**
 * A point of the climb's drawing, in the pixels its view box counts.
 */
type ClimbPoint = readonly [x: number, y: number]

/**
 * A jump set on the climb at the step `at`, its dot on the course, and the top
 * left of the tile beside it and of the mark on the tile.
 */
export interface JumpMark {
  at   : number
  dot  : ClimbPoint
  mark : ClimbPoint
  term : reward.Jump['term']
  tile : ClimbPoint
}

/**
 * The climb's tuning, its room on the left the width of its value labels and
 * its marks on tiles the size of a chip's.
 */
export const CLIMB: Climb = {
  box     : { bottom: 0, left: IDENTITY.lengths.spacing['7'], right: IDENTITY.lengths.spacing['6'], top: 0 },
  dot     : 5,
  every   : { narrow: 50, wide: 25 },
  halo    : 10,
  head    : 5.5,
  label   : plot.LABELING,
  least   : { height: 120, width: 240 },
  narrow  : 560,
  reach   : 3,
  rise    : 6,
  rug     : 10,
  strokes : IDENTITY.lengths.strokes,
  tick    : 5,
  ticks   : [0, 0.5, 1],
  title   : 44,
  top     : 1,
  tile    : {
    art    : IDENTITY.sprites.ball.frames[0]!.length,
    gap    : IDENTITY.lengths.spacing['3'],
    radius : IDENTITY.lengths.radii['1'],
    side   : IDENTITY.lengths.sizes.mark
  }
}

/**
 * Reports whether the step `traced` paid a new position.
 */
function fresh(traced: reward.Traced): boolean {
  return traced.paid.some(item => item.term === 'novelty')
}

/**
 * Draws the return's climb across `trace` at `width` by `height` pixels: a step
 * from each step's return to the next, a tick along the floor for each new
 * position, each jump's dot and mark, and the labels of its values and steps, a
 * step label left out where it would meet the axis's title.
 */
export function climbOf(
  trace  : readonly reward.Traced[],
  width  : number,
  height : number,
  climb  : Climb = CLIMB
): ClimbPlot {
  const { box, label, tile }      = climb
  const { end, floor, x: across } = plot.frameOf(box, height, width)
  const last                      = trace.length - 1
  const x                         = (step: number) => across(step, last)
  const y                         = (value: number) =>
    plot.round(box.top + (floor - box.top) * (1 - value / climb.top))
  const heads  = trace.map((each, step): ClimbPoint => [x(step), y(each.total)])
  const every  = width < climb.narrow ? climb.every.narrow : climb.every.wide
  const edge   = box.left - climb.strokes.axis / 2
  const ticks  = climb.ticks.map(value => `M${box.left - climb.tick},${y(value)}H${box.left}`)
  const marked = trace.flatMap((each, step) => fresh(each) ? [x(step)] : [])

  return {
    axis   : `M${edge},${box.top - climb.rise}V${floor + climb.strokes.axis / 2}H${end}${ticks.join('')}`,
    course : heads.map(([hx, hy], step) => step === 0 ? `M${hx},${hy}` : `H${hx}V${hy}`).join(''),
    heads  : heads,
    height : height,
    rug    : marked.map(at => `M${at},${floor}V${floor - climb.rug}`).join(''),
    title  : { anchor: 'end', text: 'Step', x: end, y: floor + label.drop },
    width  : width,

    jumps: trace.flatMap((each, step) => each.jumps.map((jump): JumpMark => {
      const [jx, jy] = [x(step), y(jump.total)]
      const beside   = jx - tile.gap - tile.side
      return {
        at   : step,
        dot  : [jx, jy],
        mark : [beside + (tile.side - tile.art) / 2, jy - tile.art / 2],
        term : jump.term,
        tile : [beside, jy - tile.side / 2]
      }
    })),

    steps: plot.multiplesOf(every, last)
      .filter(step => end - x(step) >= climb.title)
      .map(step => ({ anchor: 'middle', text: numbers.count(step), x: x(step), y: floor + label.drop })),

    values: climb.ticks.map(value => (
      { anchor: 'end', text: numbers.fixed(value, 2), x: box.left - label.gap, y: y(value) + label.baseline }
    ))
  }
}

/**
 * Measures the climb's box `box` and draws the climb across `trace` under
 * `climb` at the box's size in whole pixels, no smaller than the least the
 * climb takes, drawing nothing before the box is measured.
 */
export function useClimb(
  box   : MaybeElementRef,
  trace : readonly reward.Traced[],
  climb : Climb = CLIMB
): ComputedRef<ClimbPlot | null> {
  const { height, width } = useElementSize(box)
  const { least }         = climb
  const measured          = computed(() => width.value > 0)
  const tall              = computed(() => Math.max(least.height, Math.round(height.value)))
  const wide              = computed(() => Math.max(least.width, Math.round(width.value)))
  return computed(() => measured.value ? climbOf(trace, wide.value, tall.value, climb) : null)
}
