import { describe, expect, it } from 'vitest'

import * as argmax  from '../../../lib/results/argmax.ts'
import * as results from '../../../lib/results/results.ts'
import FIXTURE      from './fixtures/results.json' with { type: 'json' }

/**
 * Seven runs across every agent and both starts, PPO's four from seed 2 to 5.
 */
const RESULTS = FIXTURE as unknown as results.Results

/**
 * The fixture's runs laid out as they stand.
 */
const LAID = argmax.argmaxOf(RESULTS)!

/**
 * Lays out the fixture's runs with the score of PPO's seed `seed` at
 * evaluation `n` changed by `change`.
 */
function scored(seed: number, n: number, change: Partial<results.Score>): argmax.Argmax {
  const runs = RESULTS.runs.map(run => run.agent !== 'ppo' || run.seed !== seed ? run : {
    ...run,
    scores: run.scores.map((score, at) => at === n ? { ...score, ...change } : score)
  })
  return argmax.argmaxOf({ ...RESULTS, runs })!
}

describe('argmaxOf', () => {
  it('reads each PPO seed’s two shares back as counts of the episodes an evaluation plays', () => {
    const first = LAID.lanes.map(lane => [lane.group.id, lane.seeds.map(each => [each.seed, each.counts[0]])])

    expect(first).toStrictEqual([
      ['ppo-bedroom', [
        [2, { argmax: 0, differs: true, sampled: 15 }],
        [3, { argmax: 8, differs: false, sampled: 8 }]
      ]],
      ['ppo-curriculum', [
        [4, { argmax: 23, differs: false, sampled: 23 }],
        [5, { argmax: 30, differs: false, sampled: 30 }]
      ]]
    ])
  })

  it('counts the seeds differing at each evaluation beside the step the runs share there', () => {
    expect([LAID.differing, LAID.steps, LAID.seeds, LAID.episodes]).toStrictEqual([
      [1, 0, 0], [500_000, 1_000_000, 1_500_000], 4, 30
    ])
  })

})

describe('argmaxOf’s takeaway', () => {
  it('reads the takeaway from every count, the two ways differing early and matching from a step on', () => {
    expect(LAID.takeaway).toStrictEqual({
      head : 'Early in training, PPO’s most likely press misses the goal where sampling reaches it, and '
           + 'from 1.00M steps on the two match on every seed.',
      says : 'A seed’s two counts differ at 1 of PPO’s 12 evaluations, the most likely press reaching '
           + 'the goal in fewer episodes at 1 of them.'
    })
  })

  it.each([
    [2, 0, 0.5, 'PPO’s most likely press reaches the goal in as many episodes as sampling its presses '
              + 'at every evaluation.'],
    [2, 0, 1, 'Early in training, PPO’s most likely press reaches the goal where sampling misses it, '
            + 'and from 1.00M steps on the two match on every seed.'],
    [3, 2, 0, 'PPO’s most likely press misses the goal where sampling reaches it, and the two still '
            + 'differ at the last evaluation.']
  ])('reads its heading from the counts once seed %i at evaluation %i reads %d', (seed, n, to, head) => {
    expect(scored(seed, n, { argmax: to }).takeaway.head).toBe(head)
  })

})

describe('argmaxOf’s evaluations', () => {
  it('names the step most runs share, where a resumed run evaluates a rollout later', () => {
    expect(scored(2, 1, { step: 1_016_384 }).steps).toStrictEqual([500_000, 1_000_000, 1_500_000])
  })

  it('lays out the evaluations every PPO run played', () => {
    const short = RESULTS.runs.find(run => run.seed === 4)!
    const runs  = [...RESULTS.runs.filter(run => run !== short), { ...short, scores: short.scores.slice(0, 2) }]

    expect(argmax.argmaxOf({ ...RESULTS, runs })!.steps).toStrictEqual([500_000, 1_000_000])
  })

  it('lays out nothing where no PPO run is committed', () => {
    expect(argmax.argmaxOf({ ...RESULTS, runs: RESULTS.runs.filter(run => run.agent !== 'ppo') })).toBeNull()
  })

  it('reads every committed PPO share as a whole count of the episodes an evaluation plays', () => {
    const { episodes } = argmax.argmaxOf()!
    const ppo          = results.COMMITTED.runs.filter(run => run.agent === 'ppo')
    const counts       = ppo.flatMap(run => run.scores.flatMap(score => [score.reached, score.argmax!]))
                            .map(share => share * episodes)

    expect(counts.filter(count => Math.abs(count - Math.round(count)) > 1e-9)).toStrictEqual([])
  })
})

describe('evaluationText and differingText', () => {
  it.each([
    [0, 'Evaluation 1 of 3, 0.50M steps', '1 of 4 seeds differ, each marked with its count at the most '
                                        + 'likely press'],
    [2, 'Evaluation 3 of 3, 1.50M steps', 'No seed differs, so nothing is marked']
  ])('names evaluation %i and how many seeds differ there', (n, named, differing) => {
    expect([argmax.evaluationText(LAID, n), argmax.differingText(LAID, n)]).toStrictEqual([named, differing])
  })
})
