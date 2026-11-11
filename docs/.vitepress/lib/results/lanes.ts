import { type PlotLabel, round }                              from '../drawing/plot.ts'
import { type Estimate, type Group, type Verdict, verdictOf } from './results.ts'

/**
 * What a lane's verdict compares its group against, random presses under the
 * same seeds or the same agent's runs from the bedroom.
 */
export type Against = 'bedroom' | 'random'

/**
 * A side of the wide figure a reader widens, the learning curves at its left
 * or the last evaluation at its right.
 */
export type Side = 'curves' | 'finals'

/**
 * One seed's run at the last evaluation, a line from its random share at
 * `from` to its own at `to` along the height `y`.
 */
interface Bell {
  from : number
  to   : number
  y    : number
}

/**
 * One evaluation of a seed's row, its shade from 0, none of the episodes
 * reaching the goal, to 3, more than two thirds of them, and its span.
 */
export interface Cell {
  shade : 0 | 1 | 2 | 3
  width : number
  x     : number
}

/**
 * The figures laid out: its height, how far each side has folded from 0,
 * standing whole, to 1, folded to its tab, how far the verdicts have opened,
 * each group's lane, the axes along the steps and along the shares, and the
 * span of each side a reader widens, `null` where the figure stacks.
 */
export interface Lanes {
  folded : Readonly<Record<Side, number>>
  height : number
  lanes  : readonly Lane[]
  opened : number
  shares : Axis
  sides  : Readonly<Record<Side, readonly [number, number]>> | null
  steps  : Axis
}

/**
 * One group's lane: its seeds' rows of cells, its last evaluation, its name
 * and figure, where its glyph stands beside them, its verdicts, and the tab its
 * last evaluation folds to.
 */
export interface Lane {
  bells  : readonly Bell[]
  finals : Finals
  glyphs : readonly (readonly [number, number])[]
  group  : Group
  heads  : readonly PlotLabel[]
  odds   : readonly OddsLine[]
  rows   : readonly SeedRow[]
  tab    : OddsLine
}

/**
 * The probability of a higher return drawn as a whisker on a track from 0 to
 * 100%: the track's left and length, the height it sits at, the place of even
 * odds, of the estimate, and of its interval's bounds, `null` where it has no
 * interval.
 */
export interface Odds {
  at       : number
  even     : number
  interval : readonly [number, number] | null
  wide     : number
  x        : number
  y        : number
}

/**
 * One verdict of a lane, what it compares against, its odds, and the label and
 * the word set beside them.
 */
export interface OddsLine {
  label   : PlotLabel
  odds    : Odds
  verdict : Verdict
  word    : PlotLabel
}

/**
 * One seed's row of cells along the steps, the beat it traces out on, and the
 * clip it traces out through.
 */
export interface SeedRow {
  cells : readonly Cell[]
  clip  : { width: number, x: number, y: number }
  hatch : { width: number, x: number } | null
  order : number
  y     : number
}

/**
 * One axis laid out, its gridlines, the labels along it, and its title.
 */
export interface Axis {
  grid   : string
  labels : readonly PlotLabel[]
  titles : readonly PlotLabel[]
}

/**
 * A lane's last evaluation: the group's interval as a band and its
 * interquartile mean as a line, random presses' interval and interquartile
 * mean behind it, each from left to right where the interval is `null`, and
 * the height the lane spans.
 */
interface Finals {
  interval : readonly [number, number]
  mean     : number
  random   : { interval: readonly [number, number], mean: number }
  span     : readonly [number, number]
}

/**
 * The pixels the figure is laid out in: a seed's row and the gap between rows,
 * the least height of a lane and the gap between lanes, the gap between the
 * two sides, the column of names at the left, the height of a name over a lane
 * that stacks, the column of verdicts and its gap, the tab a folded side
 * keeps, the room under the lanes for the axes, the drop of a verdict set over
 * its lane, the width under which the figure stacks, the share of the width the
 * last evaluation takes at rest, and the width over which a side folds.
 */
export const LANES = {
  drop    : 42,
  facts   : 212,
  factsAt : 12,
  fold    : 160,
  folding : 60,
  foot    : 56,
  gap     : 18,
  head    : 16,
  label   : 150,
  lane    : 45,
  laneGap : 14,
  rest    : 0.46,
  row     : 7,
  rowGap  : 2.5,
  tab     : 92,
  wide    : 560
} as const

/**
 * The word each verdict sets in, against random presses and against the
 * bedroom.
 */
export const WORDS: Readonly<Record<Against, Record<Verdict, string>>> = {
  bedroom : { above: 'BETTER', below: 'WORSE', even: 'NOT CLEAR' },
  random  : { above: 'BEATS', below: 'BELOW', even: 'NOT CLEAR' }
}

/**
 * The share of episodes reaching the goal each shade past the lightest
 * rises above, a cell taking the darkest shade whose edge its share clears.
 */
export const EDGES = [0, 1 / 3, 2 / 3] as const

/**
 * Reads the shade of a cell where `share` of the episodes reached their
 * goal, one shade for each of `EDGES` the share rises above.
 */
export function shadeOf(share: number): Cell['shade'] {
  return EDGES.filter(edge => share > edge).length as Cell['shade']
}

/**
 * Reads the width the last evaluation takes in a figure `width` wide while a
 * reader widens `side`, the rest of the figure past the names folded to its
 * tab, or the share it takes at rest.
 */
export function finalsWidth(width: number, side: Side | null): number {
  const room = width - LANES.label
  return side === 'finals' ? room - LANES.tab - LANES.gap : side === 'curves' ? LANES.tab : Math.round(room * LANES.rest)
}

/**
 * Lays out the verdict of `estimate` against `against` on one line from `x` at
 * the height `y`, its label, its odds, and its word.
 */
export function oddsLine(estimate: Estimate, against: Against, x: number, y: number): OddsLine {
  const verdict = verdictOf(estimate)
  return {
    label   : { anchor: 'start', text: `VS ${against.toUpperCase()}`, x, y: y + 4 },
    odds    : oddsOf(estimate, x + 80, y, 52),
    verdict : verdict,
    word    : { anchor: 'start', text: WORDS[against][verdict], x: x + 140, y: y + 4 }
  }
}

/**
 * Lays out the odds of `estimate` on a track `wide` pixels long from `x` at
 * the height `y`.
 */
export function oddsOf(estimate: Estimate, x: number, y: number, wide: number): Odds {
  const at = (share: number) => round(x + share * wide)
  return {
    at       : at(estimate.value),
    even     : at(0.5),
    interval : estimate.interval?.map(at) as [number, number] | undefined ?? null,
    wide     : wide,
    x        : x,
    y        : y
  }
}

/**
 * The height of each lane, its seeds' rows or the least height its verdicts
 * need, whichever is taller.
 */
export function laneHeight(groups: readonly Group[]): number {
  const seeds = Math.max(...groups.map(group => group.runs.length))
  return Math.max(LANES.lane, seeds * (LANES.row + LANES.rowGap) - LANES.rowGap)
}
