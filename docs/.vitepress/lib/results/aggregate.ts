import { pickIndex, seeded }                          from '../game/random.ts'
import { AGENTS, COMMITTED, groupsOf, interquartile } from './results.ts'
import type { Estimate, Group, Results }              from './results.ts'

/**
 * The aggregate one group's runs report at their last evaluation, its share of
 * episodes reaching the goal across runs beside random presses' under the
 * same seeds.
 */
export interface Aggregate {
  group   : Group
  random  : Estimate
  reached : Estimate
}

/**
 * One run of a group at its last evaluation beside random presses under its
 * seed: its seed, its share of episodes reaching the goal, and random
 * presses' share.
 */
export interface Paired {
  random : number
  seed   : number
  share  : number
}

/**
 * The count of draws SciPy's `bootstrap` takes by default, the count behind
 * every interval the runs report.
 */
export const RESAMPLES = 9999

/**
 * Reads `share` in whole points of a percent.
 */
const points = (share: number) => Math.round(share * 100)

/**
 * Reads the quantile `q` of `values` as NumPy's `percentile` reads it by
 * default, interpolating linearly between the two values around it.
 */
function quantileOf(values: readonly number[], q: number): number {
  const sorted = values.toSorted((a, b) => a - b)
  const at     = (sorted.length - 1) * q
  const below  = Math.floor(at)
  const above  = Math.min(below + 1, sorted.length - 1)
  return sorted[below]! + (sorted[above]! - sorted[below]!) * (at - below)
}

/**
 * Spells `estimate` as a screen reader reads it, its share and its 95%
 * interval where it has one.
 */
const spokenShareOf = (estimate: Estimate) => estimate.interval
  ? `${percentOf(estimate.value)}, 95% interval ${estimate.interval.map(points).join(' to ')}%`
  : percentOf(estimate.value)

/**
 * Reads the aggregate of each group `results` holds, in the order its
 * comparisons list them.
 */
export function aggregatesOf(results: Results = COMMITTED): Aggregate[] {
  return groupsOf(results).map(group => ({
    group   : group,
    random  : group.comparison.baseline,
    reached : group.comparison.reached
  }))
}

/**
 * Reads the interquartile mean of each of `draws` draws of `shares` with
 * replacement, in the order they are drawn, from Mulberry32 seeded by `seed`.
 */
export function drawnOf(shares: readonly number[], draws: number = RESAMPLES, seed = 0): number[] {
  const random = seeded(seed)
  const drawn  = () => shares.map(() => shares[pickIndex(shares.length, random)]!)
  return Array.from({ length: draws }, () => interquartile(drawn()))
}

/**
 * Reads the estimate of `shares` the page draws itself: their interquartile
 * mean, the middle 95% of its bootstrap's draws where there are two shares or
 * more, and their count.
 */
export const estimateOf = (shares: readonly number[]): Estimate => ({
  interval : shares.length > 1 ? middleOf(drawnOf(shares)) : null,
  runs     : [shares.length],
  value    : interquartile(shares)
})

/**
 * Reads how far apart two intervals stand at their farther end, in whole
 * points of a percent.
 */
export const gapOf = (a: readonly [number, number], b: readonly [number, number]) =>
  Math.max(Math.abs(points(a[0]) - points(b[0])), Math.abs(points(a[1]) - points(b[1])))

/**
 * Reads the middle 95% of `means` as a percentile bootstrap reads its
 * interval, from the 2.5th percentile to the 97.5th.
 */
export const middleOf = (means: readonly number[]): readonly [number, number] =>
  [quantileOf(means, 0.025), quantileOf(means, 0.975)]

/**
 * Reads the runs of the group `aggregate` draws in the order of their seeds,
 * each beside random presses' share under its seed.
 */
export const pairedOf = ({ group }: Aggregate): Paired[] => group.runs
  .map(run => ({ random: run.baseline.reached, seed: run.seed, share: run.scores.at(-1)!.reached }))
  .toSorted((a, b) => a.seed - b.seed)

/**
 * Spells `share` as a whole percent.
 */
export const percentOf = (share: number) => `${points(share)}%`

/**
 * Reads the interval of `estimate`, or its value at both ends where it has
 * none.
 */
export const spanOf = (estimate: Estimate): readonly [number, number] =>
  estimate.interval ?? [estimate.value, estimate.value]

/**
 * Spells `aggregate` as a screen reader reads its column: its agent's full
 * name followed by its short one where the two differ, its start, its
 * interquartile mean with its 95% interval and its count of runs, and random
 * presses' under the same seeds.
 */
export function spokenOf({ group, random, reached }: Aggregate): string {
  const { name, short } = AGENTS[group.agent]
  const [count = 0]     = reached.runs
  const who             = name === short ? name : `${name} (${short})`
  return `${who}, ${group.curriculum ? 'with the curriculum' : 'from the bedroom'}: `
    + `interquartile mean ${spokenShareOf(reached)} over ${count} ${count === 1 ? 'run' : 'runs'}, `
    + `beside random presses under the same seeds at ${spokenShareOf(random)}`
}

/**
 * Names the runs of the group `aggregate` draws in a sentence, its agent's
 * short name followed by its start where it trained along the curriculum.
 */
export const whoOf = ({ group }: Aggregate) =>
  `${AGENTS[group.agent].short}${group.curriculum ? ' along the curriculum' : ''}`
