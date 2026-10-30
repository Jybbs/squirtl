import WORLD           from '../art/world.json' with { type: 'json' }
import SETTINGS        from '../rendered/settings.json' with { type: 'json' }
import type { Random } from './random.ts'
import * as rooms      from './rooms.ts'

/**
 * What one press in the town leads to, the state Blue stands on after it, the
 * reward it pays, and whether it ends the episode.
 */
export interface Outcome {
  done   : boolean
  next   : number
  reward : number
}

/**
 * Chooses the index of a button to press from a state of the town, drawing from
 * `random` where it chooses at random.
 */
export type Policy = (state: number, random: Random) => number

/**
 * One walk through the town under a policy, the way Blue faced after each press
 * from his first, whether it reached the north edge, the presses it took, and
 * every state it stood on.
 */
export interface Walk {
  facings : rooms.Direction[]
  reached : boolean
  steps   : number
  trail   : number[]
}

/**
 * The way Blue faces as every walk through the town starts, the house's door
 * mats taking him out on a press of Down and `PlayerStepOutFromDoor` walking
 * him down off Pallet Town's door.
 */
export const TOWN_FACING: rooms.Direction = 'down'

/**
 * Blue's square outside his door, where the house's door mats leave him and
 * every walk through the town starts.
 */
export const townStart: rooms.Square = rooms.RULES.house.exits[0].arrive

/**
 * The states of the town, one to each square of Pallet Town's walk grid.
 */
export const townStates = WORLD.pallet.w * WORLD.pallet.h

/**
 * The squares across Pallet Town's walk grid, by which a state's index counts
 * its rows.
 */
const townWidth = WORLD.pallet.w

/**
 * The state of the square outside Blue's door.
 */
export const townDoor = stateOf(townStart)

/**
 * Walks the town from Blue's door under `policy` until he reaches the north
 * edge or `budget` presses have passed, `random` feeding the policy's draws.
 *
 * Every press leaves Blue stopped, so a direction other than the one he faces
 * only turns him to face it, as pret/pokered's `OverworldLoop` sends such a
 * press through `.holdIntermediateDirectionLoop`. A press of the direction he
 * faces, or of A or B, goes through `townStep`.
 */
export function playTown(budget: number, random: Random, policy: Policy): Walk {
  const facings = [TOWN_FACING]
  const seen    = new Uint8Array(townStates)
  const trail   = [townDoor]
  let state     = townDoor
  seen[state]   = 1
  for (let step = 1; step <= budget; step++) {
    const action    = policy(state, random)
    const direction = rooms.DIRECTIONS[action]
    const facing    = facings.at(-1)!
    facings.push(direction ?? facing)
    if (direction !== undefined && direction !== facing) {
      trail.push(state)
      continue
    }
    const { done, next } = townStep(action, seen, state)
    state                = next
    trail.push(state)
    if (done) return { facings, reached: true, steps: step, trail }
  }
  return { facings, reached: false, steps: budget, trail }
}

/**
 * Reads the square of Pallet Town the state `state` names.
 */
export function squareOf(state: number): rooms.Square {
  return [state % townWidth, Math.floor(state / townWidth)]
}

/**
 * Reads the state of the town the square `at` of Pallet Town names.
 */
export function stateOf(at: rooms.Square): number {
  return at[1] * townWidth + at[0]
}

/**
 * Presses the button at index `action` with Blue on the square `state` names,
 * marking each square he reaches in `seen`.
 *
 * A direction moves him to a walkable square other than his house's door,
 * paying `novelty` where `seen` has not yet marked it and the milestone where
 * it lies on the north edge, which ends the episode. A and B, and a step onto a
 * blocked square, leave him in place and pay nothing.
 */
export function townStep(
  action  : number,
  seen    : Uint8Array,
  state   : number,
  novelty : number = SETTINGS.reward.novelty
): Outcome {
  const direction = rooms.DIRECTIONS[action]
  if (direction === undefined) return { done: false, next: state, reward: 0 }
  const from: rooms.Standing = { at: squareOf(state), place: 'pallet' }
  const to                   = rooms.neighbor(from.at, direction)
  if (!rooms.passable(to, from.place) || rooms.warpOf(from, direction)) {
    return { done: false, next: state, reward: 0 }
  }
  const next   = stateOf(to)
  const fresh  = !seen[next]
  seen[next]   = 1
  const reward = fresh ? novelty : 0
  if (to[1] <= rooms.NORTH_EDGE) return { done: true, next, reward: reward + SETTINGS.reward.milestone }
  return { done: false, next, reward }
}
