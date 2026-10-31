import { EPISODE, Episode }              from '../game/episode.ts'
import { autoPress }                     from '../game/player.ts'
import { type Random, pickFrom, seeded } from '../game/random.ts'
import * as rooms                        from '../game/rooms.ts'
import SETTINGS                          from '../rendered/settings.json' with { type: 'json' }
import type { ChipContent, KeyFigures }  from '../widgets/chips.ts'
import { count, counted }                from '../widgets/numbers.ts'

/**
 * What one episode reached, whether it chose the starter and the steps it
 * played.
 */
export interface Ending {
  reached : boolean
  steps   : number
}

/**
 * How the race's evaluation plays: the episodes each player plays, the chance
 * of a random press the agent takes, the seed of the first episode, each later
 * one taking the next, and the stops of the clock across the log scale of
 * steps, from the first step to the episode's limit.
 */
export interface Evaluating {
  episodes : number
  epsilon  : number
  first    : number
  stops    : number
}

/**
 * The chip of one of the two players the site's widgets set side by side, its
 * name and the role whose hue marks it.
 */
export interface PlayerChip extends ChipContent {
  role: Racer
}

/**
 * Each player's episodes under the same seeds, in the order of their seeds.
 */
export type Race = Readonly<Record<Racer, readonly Ending[]>>

/**
 * A player of the race, the agent or the random baseline.
 */
export type Racer = (typeof RACERS)[number]

/**
 * Chooses one press of `episode` with draws from `random`.
 */
type Presser = (episode: Episode, random: Random) => rooms.Button

/**
 * One player's entry in the race's key, its name and the role whose hue marks
 * it beside the episodes that have reached the starter and the steps those
 * episodes took on average.
 */
export interface Score extends PlayerChip {
  figures: KeyFigures
}

/**
 * The evaluation the settings declare, its episodes and its chance of a random
 * press, beside the seed its first episode starts from and a clock of a hundred
 * and twenty stops.
 */
export const EVALUATING: Evaluating = {
  episodes : SETTINGS.evaluation.episodes,
  epsilon  : SETTINGS.evaluation.epsilon,
  first    : 1000,
  stops    : 120
}

/**
 * The name each player takes on every widget.
 */
const PLAYER_NAMES: Readonly<Record<Racer, string>> = { agent: 'The agent', random: 'Random presses' }

/**
 * The presses the environment's action space holds, the six buttons and
 * pressing none, which moves Blue no more than B does in the first rooms.
 */
const PRESSES: readonly rooms.Button[] = [...rooms.BUTTONS, 'b']

/**
 * The players, the agent and the random baseline, in the order every widget
 * names them.
 */
export const RACERS = ['agent', 'random'] as const

/**
 * Each player's chip, its name beside the role whose hue marks it, in the order
 * `RACERS` lists the players.
 */
export const PLAYERS: readonly PlayerChip[] = RACERS.map(role => ({ name: PLAYER_NAMES[role], role }))

/**
 * Makes the agent's stand-in at the chance `epsilon` of a random press, which
 * otherwise walks the shortest way to each room's goal and to Squirtle's Poké
 * Ball.
 */
const agentAt = (epsilon: number): Presser => (episode, random) =>
  random() < epsilon ? pickFrom(PRESSES, random) : autoPress(episode, random, 0)

/**
 * Plays one episode from `seed` to the starter or the episode's limit, each
 * press chosen through `press`.
 */
function play(press: Presser, seed: number): Ending {
  const episode = new Episode()
  const random  = seeded(seed)
  while (!episode.done) episode.press(press(episode, random))
  return { reached: episode.flags.has('starter'), steps: episode.steps }
}

/**
 * Presses at random among the action space's presses, as the random baseline
 * does.
 */
const pressAtRandom: Presser = (_, random) => pickFrom(PRESSES, random)

/**
 * Reads the step the clock stands at on its stop `stop`, the steps rising as a
 * power of ten across the stops from the first step to the episode's limit.
 */
export function clockAt(stop: number, evaluating: Evaluating = EVALUATING): number {
  return Math.round(10 ** (stop / evaluating.stops * Math.log10(EPISODE.limit)))
}

/**
 * Describes the clock's stop `stop` of `race` for a screen reader, the step it
 * stands at and how many of each player's episodes have reached the starter by
 * it.
 */
export function describeStop(race: Race, stop: number, evaluating: Evaluating = EVALUATING): string {
  const now = clockAt(stop, evaluating)
  return `${counted(now, 'step')}: the agent has reached the starter in `
       + `${reachedBy(race.agent, now)} of ${evaluating.episodes} episodes and random presses in `
       + `${reachedBy(race.random, now)}`
}

/**
 * Plays each player's episodes of `evaluating` under the same seeds, the
 * agent's stand-in and the random baseline.
 */
export function raceOf(evaluating: Evaluating = EVALUATING): Race {
  const agent = agentAt(evaluating.epsilon)
  const seeds = Array.from({ length: evaluating.episodes }, (_, n) => evaluating.first + n)
  return {
    agent  : seeds.map(seed => play(agent, seed)),
    random : seeds.map(seed => play(pressAtRandom, seed))
  }
}

/**
 * Counts the episodes of `outcomes` that had reached the starter by the step
 * `now`.
 */
export function reachedBy(outcomes: readonly Ending[], now: number): number {
  return outcomes.filter(outcome => outcome.reached && outcome.steps <= now).length
}

/**
 * Sets each player of `race` in the key beside the episodes that had reached
 * the starter by the step `now` and the steps the episodes reaching it took on
 * average.
 */
export function scoresOf(now: number, race: Race): Score[] {
  return PLAYERS.map(({ name, role }) => {
    const endings = race[role]
    const steps   = stepsTo(endings)
    const reached = `${reachedBy(endings, now)} of ${endings.length}`
    return { figures: [reached, steps === null ? 'None' : count(Math.round(steps))], name, role }
  })
}

/**
 * Averages the steps of the episodes of `outcomes` that reached the starter, as
 * an evaluation measures its steps to the starter.
 *
 * Returns:
 *   The mean, or `null` where no episode reached the starter.
 */
export function stepsTo(outcomes: readonly Ending[]): number | null {
  const steps = outcomes.filter(outcome => outcome.reached).map(outcome => outcome.steps)
  return steps.length > 0 ? steps.reduce((sum, each) => sum + each, 0) / steps.length : null
}
