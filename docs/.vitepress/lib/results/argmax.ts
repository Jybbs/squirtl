import SETTINGS     from '../rendered/settings.json' with { type: 'json' }
import { fixed }    from '../widgets/numbers.ts'
import * as results from './results.ts'

/**
 * PPO's evaluations laid out a seed at a time: the count of seeds whose two
 * counts differ at each evaluation, the episodes each evaluation plays, the
 * runs of each start, the count of seeds across both starts, the step most
 * runs share at each evaluation, and the takeaway read from every count.
 */
export interface Argmax {
  differing : readonly number[]
  episodes  : number
  lanes     : readonly ArgmaxLane[]
  seeds     : number
  steps     : readonly number[]
  takeaway  : Takeaway
}

/**
 * PPO's runs of one start, its group beside each seed's counts at every
 * evaluation.
 */
interface ArgmaxLane {
  group : results.Group
  seeds : readonly Seeded[]
}

/**
 * One seed's two counts at one evaluation, the episodes reaching the goal
 * sampling its presses and at its most likely press, and whether they differ.
 */
interface Counts {
  argmax  : number
  differs : boolean
  sampled : number
}

/**
 * One PPO run, its seed beside its counts at each evaluation.
 */
export interface Seeded {
  counts : readonly Counts[]
  seed   : number
}

/**
 * What every count shows across PPO's evaluations, as the heading over the
 * widget and the sentence beneath it.
 */
interface Takeaway {
  head : string
  says : string
}

/**
 * Spells `step` in millions to two places.
 */
const millions = (step: number) => `${fixed(step / 1_000_000, 2)}M`

/**
 * Reads the step most of `steps` share, the first of them where no step
 * holds more, since a resumed run's evaluation can land a rollout past the
 * others'.
 */
function sharedStep(steps: readonly number[]): number {
  const tally = [...Map.groupBy(steps, step => step)]
  return tally.reduce((most, entry) => entry[1].length > most[1].length ? entry : most)[0]
}

/**
 * Reads what the counts of `seeds` show across `steps`: where the two ways of
 * playing differ early and match from some evaluation on, which way the most
 * likely press mostly differs and the step they match from, and otherwise
 * that they still differ at the last evaluation or never differ at all.
 */
function takeawayOf(seeds: readonly Seeded[], steps: readonly number[], episodes: number): Takeaway {
  const counts  = seeds.flatMap(seeded => seeded.counts)
  const differ  = counts.filter(each => each.differs)
  const fewer   = differ.filter(each => each.argmax < each.sampled).length
  const settled = (n: number) => seeds.every(seeded => seeded.counts.slice(n).every(each => !each.differs))
  const matched = steps.findIndex((_, n) => settled(n))

  if (differ.length === 0) return {
    head : 'PPO’s most likely press reaches the goal in as many episodes as sampling its presses at every '
         + 'evaluation.',
    says : `Every seed reaches the goal in as many of its ${episodes} episodes both ways at each of PPO’s `
         + `${counts.length} evaluations.`
  }

  const way  = 2 * fewer >= differ.length
    ? 'misses the goal where sampling reaches it'
    : 'reaches the goal where sampling misses it'
  const head = matched === -1
    ? `PPO’s most likely press ${way}, and the two still differ at the last evaluation.`
    : `Early in training, PPO’s most likely press ${way}, and from ${millions(steps[matched]!)} steps on `
    + 'the two match on every seed.'

  return {
    head : head,
    says : `A seed’s two counts differ at ${differ.length} of PPO’s ${counts.length} evaluations, `
         + `the most likely press reaching the goal in fewer episodes at ${fewer} of them.`
  }
}

/**
 * Lays out PPO's committed runs in `source` a seed at a time, in seed order,
 * across the evaluations every one of them played, each share read back as its
 * count of the episodes an evaluation plays by default, every PPO evaluation
 * carrying its share at the most likely press, or `null` where no PPO run is
 * committed.
 */
export function argmaxOf(source: results.Results = results.COMMITTED): Argmax | null {
  const groups = results.groupsOf(source).filter(group => group.agent === 'ppo' && group.runs.length > 0)
  if (groups.length === 0) return null

  const episodes = SETTINGS.evaluation.episodes
  const runs     = groups.flatMap(group => group.runs)
  const played   = Math.min(...runs.map(run => run.scores.length))
  const lanes    = groups.map(group => ({
    group : group,
    seeds : group.runs.toSorted((one, other) => one.seed - other.seed).map(run => ({
      seed   : run.seed,
      counts : run.scores.slice(0, played).map(score => {
        const sampled = Math.round(score.reached * episodes)
        const argmax  = Math.round(score.argmax! * episodes)
        return { argmax, differs: argmax !== sampled, sampled }
      })
    }))
  }))
  const seeds = lanes.flatMap(lane => lane.seeds)
  const steps = Array.from({ length: played }, (_, n) => sharedStep(runs.map(run => run.scores[n]!.step)))

  return {
    differing : steps.map((_, n) => seeds.filter(seeded => seeded.counts[n]!.differs).length),
    episodes  : episodes,
    lanes     : lanes,
    seeds     : seeds.length,
    steps     : steps,
    takeaway  : takeawayOf(seeds, steps, episodes)
  }
}

/**
 * States how many seeds of `argmax` differ at evaluation `n`, each marked with
 * its count at the most likely press, or that none does.
 */
export function differingText(argmax: Argmax, n: number): string {
  const differing = argmax.differing[n]!
  return differing === 0
    ? 'No seed differs, so nothing is marked'
    : `${differing} of ${argmax.seeds} seeds differ, each marked with its count at the most likely press`
}

/**
 * Names evaluation `n` of `argmax` and the step most runs share there.
 */
export function evaluationText(argmax: Argmax, n: number): string {
  return `Evaluation ${n + 1} of ${argmax.steps.length}, ${millions(argmax.steps[n]!)} steps`
}
