import { type Agent, type Estimate, type Results, interquartile } from './results.ts'

/**
 * How many episodes each made-up evaluation plays.
 */
export const EPISODES = 30

/**
 * The seeds each made-up agent trains under, and the step each of its ten
 * evaluations lands at.
 */
const SEEDS = [1, 2, 3, 4, 5] as const
const STEPS = Array.from({ length: 10 }, (_, n) => (n + 1) * 250_000)

/**
 * Each agent's made-up count of episodes reaching the goal at its last
 * evaluation under each seed, and the evaluation its runs start to rise at.
 */
const FINALS: Readonly<Record<Agent, { counts: readonly number[], rise: number }>> = {
  ppo : { counts: [27, 24, 22, 26, 18], rise: 2 },
  pqn : { counts: [19, 16, 21, 18, 14], rise: 4 },
  dqn : { counts: [2, 3, 1, 2, 3], rise: 6 }
}

/**
 * Random presses' made-up count of episodes reaching the goal under each seed.
 */
const RANDOM = [6, 8, 5, 9, 7] as const

const share = (count: number) => count / EPISODES

/**
 * Takes `values` as an estimate holding `spread` to either side of their
 * interquartile mean, within 0 and 1.
 */
const estimate = (values: readonly number[], spread: number): Estimate => {
  const value = interquartile(values)
  return {
    interval : [Math.max(0, value - spread), Math.min(1, value + spread)],
    runs     : [values.length],
    value    : value
  }
}

/**
 * Climbs a run's made-up count from none at the evaluation `rise` to `final` at
 * the last, a seed-set wobble about the climb, and reads each as a score.
 */
const scores = (final: number, rise: number, seed: number) => STEPS.map((step, n) => {
  const climb  = n < rise ? 0 : Math.min(1, (n - rise + 1) / (STEPS.length - rise))
  const wobble = climb > 0 ? ((seed * 7 + n * 3) % 5) - 2 : 0
  const count  = n === STEPS.length - 1
    ? final
    : Math.max(0, Math.min(EPISODES, Math.round(final * climb) + wobble))
  return { argmax: null, reached: share(count), reward: share(count) * 0.9 + 0.05, step: step }
})

const agents = Object.keys(FINALS) as Agent[]
const random = estimate(RANDOM.map(count => share(count)), 0.05)

/**
 * Made-up runs in the shape `squirtl write docs` writes: three agents from the
 * bedroom in the order the charts declare them, five seeds each, and random
 * presses' share under each seed, none of it a measured result.
 */
export const MADE_UP: Results = {
  comparisons : agents.map(agent => {
    const reached = estimate(FINALS[agent].counts.map(count => share(count)), 0.06)
    const odds    = reached.value > 0.7 ? 0.96 : reached.value > 0.4 ? 0.88 : 0.04
    return {
      agent      : agent,
      baseline   : random,
      beats      : {
        interval : [Math.max(0, odds - 0.14), Math.min(1, odds + 0.04)],
        runs     : [SEEDS.length, SEEDS.length],
        value    : odds
      },
      bedroom    : null,
      curriculum : false,
      reached    : reached
    }
  }),
  random : random,
  runs   : agents.flatMap(agent => SEEDS.map((seed, k) => ({
    agent      : agent,
    baseline   : { argmax: null, reached: share(RANDOM[k]!), reward: share(RANDOM[k]!) * 0.8, step: null },
    curriculum : false,
    name       : `made-up-${agent}-${seed}`,
    scores     : scores(FINALS[agent].counts[k]!, FINALS[agent].rise, seed),
    seed       : seed
  })))
}
