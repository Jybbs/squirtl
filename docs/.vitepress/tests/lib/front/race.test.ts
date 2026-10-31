import { describe, expect, it } from 'vitest'

import * as race    from '../../../lib/front/race.ts'
import { EPISODE }  from '../../../lib/game/episode.ts'
import { IDENTITY } from '../../../lib/identity/identity.ts'

/**
 * The race the settings' evaluation plays, played once for every case.
 */
const RACE = race.raceOf()

describe('raceOf', () => {
  it('plays each player’s episodes under the evaluation’s seeds, as many as the settings declare', () => {
    expect(race.RACERS.map(racer => RACE[racer].length)).toStrictEqual([30, 30])
  })

  it('has the agent’s stand-in reach the starter in every episode, and random presses in fewer', () => {
    const reached = race.RACERS.map(racer => race.reachedBy(RACE[racer], EPISODE.limit))

    expect(reached).toStrictEqual([30, 8])
  })

  it('ends every episode random presses never reach the starter in at the episode’s limit', () => {
    const missed = RACE.random.filter(outcome => !outcome.reached)

    expect(new Set(missed.map(outcome => outcome.steps))).toStrictEqual(new Set([EPISODE.limit]))
  })

  it('plays the same race again from the same seeds, and another from others', () => {
    expect(race.raceOf()).toStrictEqual(RACE)
    expect(race.raceOf({ ...race.EVALUATING, first: 2000 })).not.toStrictEqual(RACE)
  })

  it('has the agent’s stand-in reach the starter less surely pressing at random at every step', () => {
    const certain = race.raceOf({ ...race.EVALUATING, episodes: 4, epsilon: 1 })

    expect(race.reachedBy(certain.agent, EPISODE.limit)).toBeLessThan(4)
  })
})

describe('clockAt', () => {
  it.each([
    [0, 1],
    [30, 10],
    [60, 101],
    [120, EPISODE.limit]
  ])('stands the clock at stop %i on step %i, rising as a power of ten', (stop, step) => {
    expect(race.clockAt(stop)).toBe(step)
  })
})

describe('reachedBy', () => {
  it.each([
    [1, 0],
    [74, 16],
    [80, 30]
  ])('counts the agent’s episodes that had reached the starter by step %i as %i', (now, reached) => {
    expect(race.reachedBy(RACE.agent, now)).toBe(reached)
  })
})

describe('stepsTo', () => {
  it('averages the steps of the episodes that reached the starter alone', () => {
    const outcomes = [
      { reached: true, steps: 10 },
      { reached: false, steps: 99 },
      { reached: true, steps: 20 }
    ]

    expect(race.stepsTo(outcomes)).toBe(15)
  })

  it('reads no steps where no episode reached the starter', () => {
    expect(race.stepsTo([{ reached: false, steps: EPISODE.limit }])).toBeNull()
  })
})

describe('PLAYERS', () => {
  it('names the agent and then random presses, each in a role the identity gives a hue', () => {
    expect(race.PLAYERS.map(player => [player.name, player.role in IDENTITY.roles])).toStrictEqual([
      ['The agent', true], ['Random presses', true]
    ])
  })
})

describe('scoresOf', () => {
  it('sets each player beside the episodes that had reached the starter and their mean steps', () => {
    const drawn = {
      agent  : [{ reached: true, steps: 10 }, { reached: true, steps: 21 }],
      random : [{ reached: false, steps: EPISODE.limit }]
    }

    expect(race.scoresOf(15, drawn)).toStrictEqual([
      { figures: ['1 of 2', '16'], name: 'The agent', role: 'agent' },
      { figures: ['0 of 1', 'None'], name: 'Random presses', role: 'random' }
    ])
  })
})

describe('describeStop', () => {
  it.each([
    [0, '1 step: the agent has reached the starter in 0 of 30 episodes and random presses in 0'],
    [120, '10,240 steps: the agent has reached the starter in 30 of 30 episodes and random presses in 8']
  ])('describes stop %i for a screen reader', (stop, words) => {
    expect(race.describeStop(RACE, stop)).toBe(words)
  })
})
