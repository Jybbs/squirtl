import { type MaybeElementRef, clamp, refDebounced, unrefElement, useTransition } from '@vueuse/core'
import { type ComputedRef, type Ref, computed, ref, toRef }                      from 'vue'

import { type Options, usePick }    from '../widgets/choice.ts'
import { BEAT, TRAVEL }             from '../widgets/motion.ts'
import { fromMouse }                from '../widgets/scrub.ts'
import * as aggregateSwitches       from './aggregate-switches.ts'
import * as aggregate               from './aggregate.ts'
import { COMMITTED, type Estimate } from './results.ts'

/**
 * One column the plot draws: its group, the estimate the seeds kept give it,
 * and its runs in the order of their seeds.
 */
export interface Column {
  each     : aggregate.Aggregate
  estimate : Estimate
  runs     : aggregate.Paired[]
}

/**
 * How long a move takes in milliseconds: a mean, an interval, or random
 * presses' band gliding to its new place, a column's runs opening out, each
 * run a half beat behind the seed before it, a Poké Ball rocking as it lands,
 * starting two thirds of the way through its glide so every change settles in
 * about a second, and a mouse resting on a column before its runs open, which
 * a mouse passing across leaves shut.
 */
export const MOVE = {
  glide   : 4 * BEAT,
  intent  : 200,
  open    : 4 * BEAT,
  rock    : 3 * BEAT,
  stagger : BEAT / 2
} as const
/**
 * The pop a run's Poké Ball gives as its seed is switched and it empties or
 * fills, swelling, rocking to one side, and settling back.
 */
const POP: Keyframe[] = [
  { transform: 'scale(1) rotate(0deg)' },
  { transform: 'scale(1.35) rotate(-12deg)' },
  { transform: 'scale(0.92) rotate(6deg)' },
  { transform: 'scale(1) rotate(0deg)' }
]
/**
 * The settle random presses' band gives as it lands, dipping past its new
 * place and easing back onto it.
 */
export const SETTLE: Keyframe[] = [
  { transform: 'translateY(0px)' },
  { transform: 'translateY(3px)' },
  { transform: 'translateY(-1px)' },
  { transform: 'translateY(0px)' }
]
/**
 * The shake a Poké Ball gives as it lands, rocking on its foot to one side,
 * then the other, and settling, as a ball rocks in the game once it is
 * thrown.
 */
const WOBBLE: Keyframe[] = [
  { transform: 'rotate(0deg)' },
  { transform: 'rotate(-14deg)' },
  { transform: 'rotate(10deg)' },
  { transform: 'rotate(-5deg)' },
  { transform: 'rotate(0deg)' }
]
/**
 * Spells the runs of the group `each` draws as a screen reader reads them
 * once a reader opens its column, each seed's share and whether `seeds`
 * keeps it.
 */
export function spokenRunsOf(each: aggregate.Aggregate, seeds: readonly number[]): string {
  const runs  = aggregate.pairedOf(each)
  const left  = (seed: number) => seeds.includes(seed) ? '' : ', left out'
  const named = runs.map(run => `seed ${run.seed} ${aggregate.percentOf(run.share)}${left(run.seed)}`)
  return `${aggregate.whoOf(each)}, ${runs.length} runs: ${named.join('; ')}`
}

/**
 * Lays `count` marks side by side across the middle of a column `step` wide,
 * each `size` wide with `gap` between them, shrinking them where the column
 * is too narrow to hold them whole.
 *
 * Returns:
 *   How far each mark's middle stands from the column's, the distance from
 *   one mark's middle to the next, and the share of `size` each mark is drawn
 *   at.
 */
export function spreadOf(
  count : number,
  gap   : number,
  size  : number,
  step  : number
): { offsets: number[], pitch: number, scale: number } {
  const pitch = Math.min(size + gap, step / count)
  return {
    offsets : Array.from({ length: count }, (_, n) => (n - (count - 1) / 2) * pitch),
    pitch   : pitch,
    scale   : clamp((pitch - gap / 2) / size, 0, 1)
  }
}

/**
 * Reads what the plot draws over `aggregates` while `seeds` holds the seeds
 * kept: each column and random presses' estimate. With every seed kept, each
 * estimate is the one the runs report, and otherwise the page draws it again
 * from the seeds kept.
 */
export function useColumns(
  aggregates : readonly aggregate.Aggregate[],
  seeds      : Readonly<Ref<readonly number[]>>
): {
  columns : ComputedRef<Column[]>
  random  : ComputedRef<Estimate>
} {
  const baselines = new Map(COMMITTED.runs.map(run => [run.seed, run.baseline]))
  const whole     = computed(() => seeds.value.length === aggregateSwitches.committedSeeds.length)
  const keptOf    = (each: aggregate.Aggregate) =>
    aggregate.pairedOf(each).filter(run => seeds.value.includes(run.seed))
  const shownOf   = (shares: readonly number[], episodes: number, reported: Estimate) =>
    whole.value ? reported : aggregate.estimateOf(shares, episodes)
  const randoms   = computed(() => seeds.value.map(seed => baselines.get(seed)!))
  const total     = (episodes: readonly number[]) => episodes.reduce((sum, count) => sum + count, 0)

  return {
    columns : computed(() => aggregates.map(each => {
      const kept = keptOf(each)
      return {
        each     : each,
        estimate : shownOf(kept.map(run => run.share), total(kept.map(run => run.episodes)), each.reached),
        runs     : aggregate.pairedOf(each)
      }
    })),
    random  : computed(() => shownOf(
      randoms.value.map(score => score.reached),
      total(randoms.value.map(score => score.episodes)),
      COMMITTED.random!
    ))
  }
}

/**
 * Eases the share `share` reads from the share it last read to the one it
 * reads now over one glide, on the travel curve, at once where `still` holds.
 *
 * Returns:
 *   The share in whole points, which changes only when the whole point does.
 */
export function useEased(share: () => number, still: () => boolean): ComputedRef<number> {
  const eased = useTransition(share, { disabled: toRef(still), duration: MOVE.glide, easing: TRAVEL })
  return computed(() => aggregate.points(eased.value))
}

/**
 * Plays `keyframes` on each part in `parts` whose mean in `means` moved, two
 * thirds of the way through its glide, leaving a part whose mean held still,
 * and every part under reduced motion.
 *
 * Returns:
 *   The list each part's element is set in by its place.
 */
export function useLanding(
  means     : () => readonly number[],
  keyframes : Keyframe[] = WOBBLE
): (Element | null)[] {
  const parts: (Element | null)[] = []
  const landing                   = { delay: MOVE.glide * 2 / 3, duration: MOVE.rock, easing: 'ease-out' }
  aggregateSwitches.watchChanged(means, n => parts[n]?.animate(keyframes, landing))
  return parts
}

/**
 * Opens one of `count` columns laid across `plot` from `scale` pixels in to
 * its right edge: the column a mouse has rested on for `MOVE.intent`, or
 * else the one a reader picked by a press or from the keyboard, which a
 * second press closes.
 *
 * Returns:
 *   The columns' props, the column open and the one picked, by place, and the
 *   listeners the plot takes for a mouse moving over it and leaving it.
 */
export function useOpen(plot: MaybeElementRef, count: number, scale: number): {
  columns : Options<string>
  leave   : () => void
  open    : ComputedRef<number | null>
  picked  : ComputedRef<number | null>
  point   : (event: PointerEvent) => void
} {
  const names   = Array.from({ length: count }, (_, n) => `${n}`)
  const chosen  = ref<string | null>(null)
  const pointed = ref<number | null>(null)
  const rested  = refDebounced(pointed, MOVE.intent)
  const picked  = computed(() => chosen.value === null ? null : Number(chosen.value))

  return {
    columns : usePick(names, chosen),
    leave   : () => { pointed.value = null },
    open    : computed(() => rested.value ?? picked.value),
    picked  : picked,
    point   : event => {
      if (!fromMouse(event)) return
      const { left, width } = unrefElement(plot)!.getBoundingClientRect()
      const n               = Math.floor((event.clientX - left - scale) / ((width - scale) / count))
      pointed.value         = n >= 0 && n < count ? n : null
    }
  }
}

/**
 * Pops the Poké Ball of each run whose seed `seeds` switches, in every
 * column, as it empties or fills, none under reduced motion.
 *
 * Returns:
 *   The lists each run's element is set in, one per seed in the order of
 *   `committedSeeds`, by its column's place.
 */
export function useSwitched(seeds: () => readonly number[]): (Element | null)[][] {
  const runs = aggregateSwitches.committedSeeds.map(() => [] as (Element | null)[])
  const pop  = { duration: MOVE.rock, easing: 'ease-out' }
  aggregateSwitches.watchSwitched(seeds, k => runs[k]!.forEach(run => run?.animate(POP, pop)))
  return runs
}
