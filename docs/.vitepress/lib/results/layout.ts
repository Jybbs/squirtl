import { clamp } from '@vueuse/core'

import { type PlotLabel, multiplesOf, round }                                                                                from '../drawing/plot.ts'
import { type Axis, type Lane, type Lanes, LANES, type OddsLine, WORDS, finalsWidth, laneHeight, oddsLine, oddsOf, shadeOf } from './lanes.ts'
import { AGENTS, type Estimate, type Group, percent, verdictOf }                                                             from './results.ts'

/**
 * Clamps `t` between 0 and 1.
 */
const clamped = (t: number) => clamp(t, 0, 1)

/**
 * Lays out the figure of `groups` at `width` pixels with its last evaluation
 * `finals` wide, side by side from 560px and stacked under it.
 */
export function lanesOf(groups: readonly Group[], width: number, finals: number): Lanes {
  return width < LANES.wide ? stackedOf(groups, width) : wideOf(groups, width, finals)
}

/**
 * The step of the evaluation read last across `groups`, the end of the steps'
 * axis.
 */
function lastOf(groups: readonly Group[]): number {
  return Math.max(...groups.flatMap(group => group.runs.flatMap(run => run.scores.map(score => score.step))))
}

/**
 * Lays out the figure side by side at `width` pixels: the names in a column at
 * the left, the learning curves, and the last evaluation `finals` wide at the
 * right, whose verdicts open as it widens from its share at rest and which
 * folds either side to its tab under 160px.
 */
function wideOf(groups: readonly Group[], width: number, finals: number): Lanes {
  const tall   = laneHeight(groups)
  const pitch  = tall + LANES.laneGap
  const bottom = groups.length * pitch - LANES.laneGap
  const x0     = LANES.label
  const f0     = round(width - finals)
  const x1     = f0 - LANES.gap
  const rest   = finalsWidth(width, null)
  const opened = clamped((finals - rest) / Math.max(1, finalsWidth(width, 'finals') - rest))
  const s0     = f0 + 2
  const s1     = round(width - 6 - (LANES.facts + LANES.factsAt) * opened)
  const last   = lastOf(groups)
  const lanes  = groups.map((group, n) => {
    const lane = n * pitch
    const at   = { factsX: s1 + 6 + LANES.factsAt, factsY: lane, height: tall, lane, last, s0, s1, tabX: (f0 + width) / 2, x0, x1 }
    return { ...laneOf(group, at), glyphs: [[6, lane + 8] as const], heads: headsOf(group, 18, lane + 12, null) }
  })

  return {
    folded : { curves: clamped((LANES.fold - (x1 - x0)) / LANES.folding), finals: clamped((LANES.fold - finals) / LANES.folding) },
    height : bottom + LANES.foot,
    lanes  : lanes,
    opened : opened,
    shares : sharesAxis(s0, s1, bottom + 2, lanes.map(lane => lane.finals.span)),
    sides  : { curves: [x0, round(x1 + LANES.gap / 2)], finals: [round(x1 + LANES.gap / 2), width] },
    steps  : stepsAxis(x0, x1, bottom, last)
  }
}

/**
 * Lays out the figure stacked at `width` pixels: the learning curves across
 * the width with each name over its lane, then the last evaluation beneath
 * with its verdicts beside each lane, or over it where they would leave its
 * scale under 200px.
 */
function stackedOf(groups: readonly Group[], width: number): Lanes {
  const tall   = laneHeight(groups)
  const pitch  = LANES.head + tall + LANES.laneGap
  const b1     = groups.length * pitch - LANES.laneGap
  const last   = lastOf(groups)
  const steps  = stepsAxis(0, width, b1, last)
  const over   = width - LANES.facts - LANES.factsAt < 200
  const drop   = over ? LANES.drop : 0
  const t2     = b1 + 34 + steps.titles.length * 16 + 22
  const pitch2 = tall + 12 + drop
  const s0     = 20
  const s1     = over ? width - 6 : width - LANES.facts - LANES.factsAt
  const b2     = t2 + groups.length * pitch2 - 12
  const lanes  = groups.map((group, n) => {
    const top   = n * pitch
    const lane  = t2 + n * pitch2 + drop
    const curve = laneOf(group, { factsX: 0, factsY: 0, height: tall, lane: top + LANES.head, last, s0, s1, tabX: 0, x0: 0, x1: width })
    const final = laneOf(group, { factsX: over ? s0 : s1 + LANES.factsAt, factsY: lane - drop, height: tall, lane, last, s0, s1, tabX: 0, x0: 0, x1: width })
    return { ...final, glyphs: [[6, top + 7] as const, [6, lane + tall / 2] as const], heads: headsOf(group, 18, top + 11, width), rows: curve.rows }
  })

  return {
    folded : { curves: 0, finals: 0 },
    height : b2 + LANES.foot,
    lanes  : lanes,
    opened : 1,
    shares : sharesAxis(s0, s1, b2 + 2, lanes.map(lane => lane.finals.span)),
    sides  : null,
    steps  : steps
  }
}

/**
 * Lays out the steps' axis from `left` to `right` under lanes ending at
 * `bottom`, a gridline at every half million up to `last`, every one labeled
 * from 240px and the ends alone under it, and its title over two lines under
 * 230px.
 */
function stepsAxis(left: number, right: number, bottom: number, last: number): Axis {
  const x      = (step: number) => round(left + step / last * (right - left))
  const steps  = multiplesOf(500_000, last)
  const shown  = right - left >= 240 ? steps : [steps[0]!, steps.at(-1)!]
  const titles = right - left < 230 ? ['Environment steps', '(millions)'] : ['Environment steps (millions)']
  return {
    grid   : steps.map(step => `M${x(step)},0V${round(bottom)}`).join(''),
    labels : shown.map((step, n) => ({
      anchor : n === 0 ? 'start' : n === shown.length - 1 && step !== 0 ? 'end' : 'middle',
      text   : String(step / 1_000_000),
      x      : x(step),
      y      : bottom + 16
    })),
    titles : titles.map((text, n) => ({ anchor: 'middle', text, x: round((left + right) / 2), y: bottom + 34 + n * 16 }))
  }
}

/**
 * Lays out the shares' axis from `left` to `right` at the foot `y`, gridlines
 * down each of `spans`, every quarter labeled from 220px and every half under
 * it, and its title over two lines under 200px.
 */
function sharesAxis(left: number, right: number, y: number, spans: readonly (readonly [number, number])[]): Axis {
  const x      = (share: number) => round(left + share * (right - left))
  const shares = right - left < 220 ? [0, 0.5, 1] : [0, 0.25, 0.5, 0.75, 1]
  const titles = right - left < 200 ? ['Last evaluation', '(% reaching it)'] : ['Last evaluation (% reaching it)']
  return {
    grid   : spans.flatMap(([top, tall]) => [0, 0.25, 0.5, 0.75, 1].map(share => `M${x(share)},${round(top)}V${round(top + tall)}`)).join(''),
    labels : shares.map((share, n) => ({
      anchor : n === 0 ? 'start' : n === shares.length - 1 ? 'end' : 'middle',
      text   : `${share * 100}%`,
      x      : x(share),
      y      : y + 14
    })),
    titles : titles.map((text, n) => ({ anchor: 'middle', text, x: round((left + right) / 2), y: y + 32 + n * 16 }))
  }
}

/**
 * Names a group in the code face's capitals, its agent and its start.
 */
function capsOf(group: Group): string {
  return `${AGENTS[group.agent].short} · ${group.curriculum ? 'CURRICULUM' : 'BEDROOM'}`
}

/**
 * Lays out one group's lane at the height `lane` from the parts each layout
 * places: its rows from `x0` to `x1` up to the step `last`, its last
 * evaluation from `s0` to `s1`, its verdicts from `factsX` at `factsY`, and its
 * tab centered on `tabX`.
 */
function laneOf(group: Group, at: LanePlaces): Omit<Lane, 'glyphs' | 'heads'> {
  const { factsX, factsY, last, lane, s0, s1, tabX, x0, x1 } = at
  const x       = (step: number) => x0 + step / last * (x1 - x0)
  const fx      = (share: number) => round(s0 + share * (s1 - s0))
  const rowY    = (k: number) => lane + k * (LANES.row + LANES.rowGap)
  const tall    = at.height
  const between = (estimate: Estimate) => (estimate.interval ?? [estimate.value, estimate.value]).map(share => fx(share)) as [number, number]
  const bedroom = group.comparison.bedroom

  return {
    bells  : group.runs.map((run, k) => ({ from: fx(run.baseline.reached), to: fx(run.scores.at(-1)!.reached), y: rowY(k) + LANES.row / 2 })),
    finals : {
      interval : between(group.comparison.reached),
      mean     : fx(group.comparison.reached.value),
      random   : { interval: between(group.comparison.baseline), mean: fx(group.comparison.baseline.value) },
      span     : [lane - 4, tall + 8]
    },
    group : group,
    odds  : [
      oddsLine(group.comparison.beats, 'random', factsX, factsY + 9),
      ...bedroom ? [oddsLine(bedroom, 'bedroom', factsX, factsY + 29)] : []
    ],
    rows : group.runs.map((run, k) => ({
      cells : run.scores.map((score, i) => {
        const from = x(i === 0 ? 0 : run.scores[i - 1]!.step)
        return { shade: shadeOf(score.reached), width: round(Math.max(0.5, x(score.step) - from - 1)), x: round(from + 0.5) }
      }),
      clip  : { width: round(x1 - x0 + 4), x: round(x0 - 2), y: rowY(k) - 1 },
      hatch : group.curriculum ? { width: round(x(run.scores.at(-1)!.step) - x0), x: x0 } : null,
      order : k,
      y     : round(rowY(k))
    })),
    tab : tabOf(group.comparison.beats, tabX, lane)
  }
}

/**
 * Where `laneOf` places a lane's parts.
 */
interface LanePlaces {
  factsX : number
  factsY : number
  height : number
  lane   : number
  last   : number
  s0     : number
  s1     : number
  tabX   : number
  x0     : number
  x1     : number
}

/**
 * Lays out the tab a folded last evaluation keeps, centered on `x` beside the
 * lane at `lane`: the verdict against random presses over its odds over what it
 * compares against.
 */
function tabOf(estimate: Estimate, x: number, lane: number): OddsLine {
  const verdict = verdictOf(estimate)
  return {
    label   : { anchor: 'middle', text: 'VS RANDOM', x, y: lane + 41 },
    odds    : oddsOf(estimate, x - 30, lane + 23, 60),
    verdict : verdict,
    word    : { anchor: 'middle', text: WORDS.random[verdict], x, y: lane + 12 }
  }
}

/**
 * The figure's head for a lane, the group's name in capitals and the
 * interquartile mean of its share reaching the starter with its interval,
 * at `x` and `y` with the figure under the name or at `end` on its line.
 */
function headsOf(group: Group, x: number, y: number, end: number | null): PlotLabel[] {
  const figure = percent(group.comparison.reached)
  return [
    { anchor: 'start', text: capsOf(group), x, y },
    end === null ? { anchor: 'start', text: figure, x, y: y + 15 } : { anchor: 'end', text: figure, x: end, y }
  ]
}
