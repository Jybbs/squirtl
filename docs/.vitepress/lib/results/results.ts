import RESULTS                from '../rendered/results.json' with { type: 'json' }
import { type Hue, IDENTITY } from '../identity/identity.ts'
import type { KeyEntry }      from '../widgets/chips.ts'
import { count, fixed }       from '../widgets/numbers.ts'
import { glyphOf }            from './marks.ts'

/**
 * An agent a run trains, by the value `squirtl train --agent.algorithm` takes.
 */
export type Agent = keyof typeof AGENTS

/**
 * The runs of one agent, trained with or without the curriculum, set against
 * the random baseline under the same seeds at each run's last evaluation and,
 * with the curriculum, against the same agent's runs from the bedroom, as
 * `squirtl.docs.results.Comparison` writes it.
 */
interface Comparison {
  agent      : Agent
  baseline   : Estimate
  bedroom    : Estimate | null
  beats      : Estimate
  curriculum : boolean
  reached    : Estimate
}

/**
 * A statistic over runs beside its 95% percentile bootstrap interval, `null`
 * where a sample holds one run, and the count of runs in each sample.
 */
export interface Estimate {
  interval : readonly [number, number] | null
  runs     : readonly number[]
  value    : number
}

/**
 * The runs of one agent and one curriculum the charts set apart: the agent,
 * the comparison, whether the runs trained along the curriculum, the hue the
 * agent takes, the key a control names them by, the name a reader reads for
 * them, and the runs.
 */
export interface Group {
  agent      : Agent
  comparison : Comparison
  curriculum : boolean
  hue        : Hue
  id         : string
  name       : string
  runs       : readonly Trained[]
}

/**
 * Every committed run beside the comparison of each agent's runs against the
 * random baseline and random presses' share across every run, `null` where no
 * run is committed, as `squirtl write docs` writes them.
 */
export interface Results {
  comparisons : readonly Comparison[]
  random      : Estimate | null
  runs        : readonly Trained[]
}

/**
 * What one evaluation of the agent measured, the share of its episodes
 * reaching the starter and their mean return, at the step of the run it read.
 */
export interface Score {
  reached : number
  reward  : number
  step    : number
}

/**
 * One committed run, the agent's score at each evaluation beside the random
 * baseline's under the same seeds.
 */
interface Trained {
  agent      : Agent
  baseline   : Omit<Score, 'step'> & { step: null }
  curriculum : boolean
  name       : string
  scores     : readonly Score[]
  seed       : number
}

/**
 * Where an agent stands against what it is compared with: above where the 95%
 * interval of the probability that it scores higher clears even odds, below
 * where the interval stays under them, and even where it holds them or no
 * interval is drawn.
 */
export type Verdict = 'above' | 'below' | 'even'

/**
 * The name a reader reads for each agent and its name in the code face's
 * capitals, in the order the agents take the identity's series hues.
 */
export const AGENTS = {
  ppo : { name: 'PPO', short: 'PPO' },
  pqn : { name: 'PQN', short: 'PQN' },
  dqn : { name: 'Deep Q-network', short: 'DQN' }
} as const satisfies Record<string, { name: string, short: string }>

/**
 * The runs `docs/runs/` holds, as `squirtl write docs` last wrote them, read
 * through `unknown` since a JSON import types each agent as any string.
 */
export const COMMITTED = RESULTS as unknown as Results

/**
 * Pairs each comparison in `results` with its runs, under its agent's name,
 * followed by the curriculum where its runs trained along one.
 */
export function groupsOf(results: Results = COMMITTED): Group[] {
  return results.comparisons.map(comparison => ({
    agent      : comparison.agent,
    comparison : comparison,
    curriculum : comparison.curriculum,
    hue        : hueOf(comparison.agent),
    id         : `${comparison.agent}-${comparison.curriculum ? 'curriculum' : 'bedroom'}`,
    name       : `${AGENTS[comparison.agent].name}${comparison.curriculum ? ', curriculum' : ''}`,
    runs       : results.runs.filter(run =>
      run.agent === comparison.agent && run.curriculum === comparison.curriculum)
  }))
}

/**
 * Reads the series hue `agent` takes, the one at its place in the identity's
 * categorical order.
 */
export function hueOf(agent: Agent): Hue {
  return IDENTITY.order[Object.keys(AGENTS).indexOf(agent)] as Hue
}

/**
 * Takes the interquartile mean of `values` as SciPy's `trim_mean` at 0.25
 * takes it, the mean of the values left once `⌊n / 4⌋` are cut from each end,
 * every value where there are fewer than four, the statistic
 * `squirtl.evaluation` aggregates runs by.
 */
export function interquartile(values: readonly number[]): number {
  const cut  = Math.floor(values.length / 4)
  const kept = values.toSorted((a, b) => a - b).slice(cut, values.length - cut)
  return kept.reduce((sum, value) => sum + value, 0) / kept.length
}

/**
 * Reads the interquartile mean across the runs of `group` at each evaluation
 * any of them played, its share reaching the starter at the interquartile mean
 * of the steps the runs had taken by then.
 */
export function meansOf(group: Group): Score[] {
  const evaluations = Math.max(...group.runs.map(run => run.scores.length))
  return Array.from({ length: evaluations }, (_, n) => {
    const scores = group.runs.flatMap(run => run.scores[n] ?? [])
    return {
      reached : interquartile(scores.map(score => score.reached)),
      reward  : interquartile(scores.map(score => score.reward)),
      step    : interquartile(scores.map(score => score.step))
    }
  })
}

/**
 * Spells `estimate` as its value to two places, its interval in brackets where
 * it has one, and the count of runs behind it.
 */
export function spelled(estimate: Estimate): string {
  const bounds = estimate.interval ? ` [${estimate.interval.map(bound => fixed(bound, 2)).join(', ')}]` : ''
  return `${fixed(estimate.value, 2)}${bounds} over ${estimate.runs.map(count).join(' and ')}`
}

/**
 * Reads `share` in whole points of a percent.
 */
const points = (share: number) => Math.round(share * 100)

/**
 * Spells `estimate` of a share as a whole percent, its interval's bounds in
 * whole points in brackets where it has one.
 */
export function percent(estimate: Estimate): string {
  const bounds = estimate.interval ? ` [${estimate.interval.map(share => points(share)).join(', ')}]` : ''
  return `${points(estimate.value)}%${bounds}`
}

/**
 * Reads where `estimate`, a probability of scoring higher, stands against
 * even odds by its 95% interval.
 */
export function verdictOf(estimate: Estimate): Verdict {
  const [low, high] = estimate.interval ?? [0, 1]
  return low > 0.5 ? 'above' : high < 0.5 ? 'below' : 'even'
}

/**
 * Lists the figures under the curves, each group's chip in its agent's hue
 * while `pressed` holds it and in none otherwise, beside the interquartile mean
 * of its runs' share reaching the starter and the probability that a run of it
 * beats a run of random presses on mean return, then `random`, the share
 * random presses reach across every run.
 */
export function figuresOf(groups: readonly Group[], random: Estimate, pressed: ReadonlySet<string>): KeyEntry[] {
  return [
    ...groups.map(group => ({
      figures : [spelled(group.comparison.reached), spelled(group.comparison.beats)] as const,
      hue     : pressed.has(group.id) ? group.hue : null,
      mark    : glyphOf(group),
      name    : group.name,
      role    : 'none' as const
    })),
    { figures: [spelled(random), ''] as const, name: 'Random presses', role: 'random' }
  ]
}
