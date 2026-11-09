import RESULTS                                        from '../rendered/results.json' with { type: 'json' }
import { type Frame, type PlotLabel, frameOf, round } from '../drawing/plot.ts'
import { IDENTITY }                                   from '../identity/identity.ts'
import type { KeyEntry }                              from '../widgets/chips.ts'
import { count, fixed }                               from '../widgets/numbers.ts'

/**
 * The runs of one agent, trained with or without the curriculum, set against
 * the random baseline under the same seeds at each run's last evaluation, as
 * `squirtl.docs.results.Comparison` writes it.
 */
interface Comparison {
  agent      : Agent
  baseline   : Estimate
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
 * The runs of one agent and one curriculum the charts set apart, under the name
 * a reader reads for them.
 */
export interface Group {
  agent      : Agent
  comparison : Comparison
  curriculum : boolean
  name       : string
  runs       : readonly Trained[]
}

/**
 * Every committed run beside the comparison of each agent's runs against the
 * random baseline, as `squirtl write docs` writes them.
 */
export interface Results {
  comparisons : readonly Comparison[]
  runs        : readonly Trained[]
}

/**
 * What one evaluation of the agent measured, the share of its episodes
 * reaching the starter and their mean return, at the step of the run it read.
 */
interface Score {
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
 * An agent a run trains, by the value `squirtl train --agent.algorithm` takes.
 */
type Agent = keyof typeof AGENTS

/**
 * The name a reader reads for each agent.
 */
const AGENTS = { dqn: 'Deep Q-network', ppo: 'PPO', pqn: 'PQN' } as const

/**
 * The runs `docs/runs/` holds, as `squirtl write docs` last wrote them.
 */
export const COMMITTED = RESULTS as Results

/**
 * The room each plot leaves on each side for its labels, in the pixels its
 * view box counts, the drop of an axis's label below the floor and its gap
 * from the axis, the height of the learning curves' plot and of each row of
 * the comparison, the shares of the episodes reaching the starter its axis
 * labels, and the distance of each sample's line from the middle of its row.
 */
export const PLOTTING = {
  drop   : 20,
  gap    : IDENTITY.lengths.spacing['2'],
  height : IDENTITY.lengths.sizes['results-plot'],
  row    : IDENTITY.lengths.spacing['7'],
  shares : [0, 0.25, 0.5, 0.75, 1],
  split  : IDENTITY.lengths.spacing['2'],
  box    : {
    bottom : IDENTITY.lengths.spacing['7'],
    left   : IDENTITY.lengths.spacing['7'],
    right  : IDENTITY.lengths.spacing['4'],
    top    : IDENTITY.lengths.spacing['3']
  }
} as const

/**
 * Pairs each comparison in `results` with its runs, under its agent's name,
 * followed by the curriculum where its runs trained along one.
 */
export function groupsOf(results: Results = COMMITTED): Group[] {
  return results.comparisons.map(comparison => ({
    agent      : comparison.agent,
    comparison : comparison,
    curriculum : comparison.curriculum,
    name       : `${AGENTS[comparison.agent]}${comparison.curriculum ? ', curriculum' : ''}`,
    runs       : results.runs.filter(run =>
      run.agent === comparison.agent && run.curriculum === comparison.curriculum)
  }))
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
 * Lists the key of `group`'s comparison, the agent's runs and the random
 * baseline's each with the interquartile mean of the share reaching the
 * starter, and the probability that a run of the agent beats a run of random
 * presses on mean return.
 */
export function keyOf(group: Group): KeyEntry[] {
  const { baseline, beats, reached } = group.comparison
  return [
    { figures: [spelled(reached), ''], name: group.name, role: 'agent' },
    { figures: [spelled(baseline), spelled(beats)], name: 'Random presses', role: 'random' }
  ]
}

/**
 * Lays out the learning curves of `group` at `height` by `width` pixels, each
 * run's share reaching the starter across its evaluations on a line, the
 * random baseline's interquartile mean as a level line, and the steps along
 * the bottom up to the run that trained longest.
 */
export function curvesOf(group: Group, height: number, width: number): Curves {
  const frame = frameOf(PLOTTING.box, height, width)
  const last  = Math.max(...group.runs.flatMap(run => run.scores.map(score => score.step)))
  const point = (score: Score) => `${frame.x(score.step, last)},${frame.y(score.reached, 1)}`
  const left  = frame.x(0, 1)

  return {
    baseline : frame.y(group.comparison.baseline.value, 1),
    frame    : frame,
    grid     : PLOTTING.shares.map(share => `M${left},${frame.y(share, 1)}H${frame.end}`).join(''),
    last     : last,
    lines    : group.runs.map(run => `M${run.scores.map(point).join('L')}`),
    labels   : [
      ...PLOTTING.shares.map(share => shareLabel(share, left - PLOTTING.gap, frame.y(share, 1) + PLOTTING.gap / 2, 'end')),
      { anchor: 'start', text: '0', x: left, y: frame.floor + PLOTTING.drop },
      { anchor: 'end', text: count(last), x: frame.end, y: frame.floor + PLOTTING.drop }
    ]
  }
}

/**
 * The comparison of every group laid out in a strip at `width` pixels, one row
 * a group, each run's share reaching the starter at its last evaluation as a
 * dot beside its baseline's, and each sample's interquartile mean as a tick
 * across its interval.
 */
export function comparisonOf(groups: readonly Group[], width: number): Strip {
  const top    = PLOTTING.box.top
  const height = top + groups.length * PLOTTING.row + PLOTTING.box.bottom
  const frame  = frameOf({ ...PLOTTING.box, left: PLOTTING.box.left * 3 }, height, width)
  const x      = (share: number) => frame.x(share, 1)
  const sample = (estimate: Estimate, shares: readonly number[], y: number): Sample => ({
    dots     : shares.map(share => x(share)),
    interval : estimate.interval?.map(share => x(share)) as [number, number] | undefined ?? null,
    mean     : x(estimate.value),
    y        : y
  })

  return {
    floor  : frame.floor,
    grid   : PLOTTING.shares.map(share => `M${x(share)},${top}V${frame.floor}`).join(''),
    height : height,
    labels : PLOTTING.shares.map(share => shareLabel(share, x(share), frame.floor + PLOTTING.drop, 'middle')),
    rows   : groups.map((group, n) => {
      const middle = top + (n + 0.5) * PLOTTING.row
      return {
        agent  : sample(group.comparison.reached, group.runs.map(run => run.scores.at(-1)!.reached), round(middle - PLOTTING.split)),
        name   : { anchor: 'end', text: group.name, x: x(0) - PLOTTING.gap, y: middle + PLOTTING.gap / 2 },
        random : sample(group.comparison.baseline, group.runs.map(run => run.baseline.reached), round(middle + PLOTTING.split))
      }
    }),
    width  : width
  }
}

/**
 * Labels `share` of the episodes as a percent at the point (`x`, `y`).
 */
function shareLabel(share: number, x: number, y: number, anchor: PlotLabel['anchor']): PlotLabel {
  return { anchor, text: `${share * 100}%`, x, y }
}

/**
 * The learning curves of one group laid out in a plot: the plot's frame, the
 * height of the baseline's level line, the gridlines at each labeled share,
 * the last step the plot reaches, the path of each run's line, and the labels
 * along both axes.
 */
export interface Curves {
  baseline : number
  frame    : Frame
  grid     : string
  labels   : readonly PlotLabel[]
  last     : number
  lines    : readonly string[]
}

/**
 * One sample of a comparison's row, each run's dot along the row, the
 * interval's ends and the interquartile mean's place where it has one, and the
 * height its line sits at.
 */
export interface Sample {
  dots     : readonly number[]
  interval : readonly [number, number] | null
  mean     : number
  y        : number
}

/**
 * The comparison laid out: the floor, the gridlines at each labeled share, the
 * strip's height and width, the labels along the bottom, and each group's row,
 * its name beside the agent's sample and the random baseline's.
 */
export interface Strip {
  floor  : number
  grid   : string
  height : number
  labels : readonly PlotLabel[]
  rows   : readonly { agent: Sample, name: PlotLabel, random: Sample }[]
  width  : number
}
