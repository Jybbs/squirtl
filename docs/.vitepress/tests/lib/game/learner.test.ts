import { describe, expect, it } from 'vitest'

import * as learner          from '../../../lib/game/learner.ts'
import { pickIndex, seeded } from '../../../lib/game/random.ts'
import * as town             from '../../../lib/game/town.ts'
import SETTINGS              from '../../../lib/rendered/settings.json' with { type: 'json' }

describe('epsilonAt', () => {
  it.each([
    [0, learner.SCHEDULE.start],
    [2000, (learner.SCHEDULE.start + learner.SCHEDULE.end) / 2],
    [4000, learner.SCHEDULE.end],
    [40000, learner.SCHEDULE.end]
  ])('falls along the schedule to %f at step %i of 40,000', (step, epsilon) => {
    expect(learner.epsilonAt(step, 40000)).toBeCloseTo(epsilon, 12)
  })

  it('reads its schedule from the agent’s settings unless given another', () => {
    const { epsilon_end: end, epsilon_start: start, exploration_fraction: fraction } = SETTINGS.agent

    expect([learner.SCHEDULE, learner.epsilonAt(5, 10, { end: 0, fraction: 1, start: 1 })])
      .toStrictEqual([{ end, fraction, start }, 0.5])
  })
})

describe('Learner', () => {
  it('trains from seed 3 through the board’s episodes, read after 6, 30, 40, and 50', () => {
    const trained = new learner.Learner({ budget: 40000, seed: 3 })
    const reached = [6, 30, 40, 50].map(episodes => {
      while (trained.lengths.length < episodes) trained.step()
      return [trained.total, trained.lengths.at(-1)]
    })

    expect(reached).toStrictEqual([
      [2257, { length: 257, reached: true }], [11202, { length: 400, reached: false }],
      [13847, { length: 104, reached: true }], [16389, { length: 14, reached: true }]
    ])
    expect(trained.lengths.slice(0, 3))
      .toStrictEqual(Array.from({ length: 3 }, () => ({ length: 400, reached: false })))
  })

  it('fills the board’s table under the board’s discount of 0.997', () => {
    const trained = new learner.Learner({ budget: 40000, discount: 0.997, seed: 3 })
    while (trained.lengths.length < 50) trained.step()

    expect(trained.q.reduce((sum, value) => sum + value, 0)).toBe(0.8386297601246042)
  })

  it('moves the first press onto the north edge toward the milestone and starts again at the door', () => {
    const trained = new learner.Learner({ budget: 40000, seed: 3 })
    while (!trained.lengths.at(-1)?.reached) trained.step()
    const index = town.stateOf([10, 2]) * 6

    expect([trained.q[index], trained.state, trained.length])
      .toStrictEqual([Math.fround(learner.LEARNING.alpha * SETTINGS.reward.milestone), town.townDoor, 0])
  })
})

describe('Learner untrained', () => {
  it('starts fully exploring, breaks a tie with one draw, and reads an untrained square as 0', () => {
    const fresh = new learner.Learner()

    expect([fresh.epsilon, fresh.best(town.townDoor), fresh.value(town.townDoor)])
      .toStrictEqual([learner.SCHEDULE.start, pickIndex(6, seeded(1)), 0])
  })

  it('learns by default under the agent’s discount and its exploration schedule', () => {
    expect([new learner.Learner().settings, learner.LEARNING.discount, learner.LEARNING.schedule])
      .toStrictEqual([learner.LEARNING, SETTINGS.agent.discount, learner.SCHEDULE])
  })
})
