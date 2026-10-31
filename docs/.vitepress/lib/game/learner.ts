import SETTINGS    from '../rendered/settings.json' with { type: 'json' }
import * as random from './random.ts'
import * as rooms  from './rooms.ts'
import * as town   from './town.ts'

/**
 * One finished episode of the town learner, its presses and whether Blue
 * reached the north edge before the cap.
 */
export interface Lap {
  length  : number
  reached : boolean
}

/**
 * How the town learner trains: the share of each error its table takes in, the
 * steps its exploration schedule runs over, the presses an episode stops at,
 * the discount, what a new square pays, the schedule, and the seed its draws
 * start from.
 */
export interface Learning {
  alpha    : number
  budget   : number
  cap      : number
  discount : number
  novelty  : number
  schedule : Schedule
  seed     : number
}

/**
 * The exploration schedule, epsilon falling in a straight line from `start` to
 * `end` over the share `fraction` of the steps and holding there.
 */
export interface Schedule {
  end      : number
  fraction : number
  start    : number
}

/**
 * The exploration schedule the agent's settings declare.
 */
export const SCHEDULE: Schedule = {
  end      : SETTINGS.agent.epsilon_end,
  fraction : SETTINGS.agent.exploration_fraction,
  start    : SETTINGS.agent.epsilon_start
}

/**
 * How the town learner trains unless given otherwise, its table paid the
 * milestone alone and discounting by the agent's discount on the agent's
 * schedule.
 */
export const LEARNING: Learning = {
  alpha    : 0.5,
  budget   : 40000,
  cap      : 400,
  discount : SETTINGS.agent.discount,
  novelty  : 0,
  schedule : SCHEDULE,
  seed     : 1
}

/**
 * A table of values trained over Pallet Town by one-step Q-learning, a row of
 * one value per button for each square, Blue starting each episode outside his
 * door and the episode ending at the north edge, where Oak stops him, or at the
 * cap.
 *
 * Each step chooses the button its row ranks first, breaking ties at random, or
 * at epsilon's rate a button at random, and moves that button's value toward
 * the reward plus the discounted value of the next square's best button.
 * `lengths` lists every finished episode.
 */
export class Learner {
  length! : number
  seen!   : Uint8Array
  state!  : number
  total   = 0

  readonly lengths  : Lap[]        = []
  readonly q        : Float32Array = new Float32Array(town.townStates * rooms.BUTTONS.length)
  readonly random   : random.Random
  readonly settings : Learning

  constructor(learning: Partial<Learning> = {}) {
    this.settings = { ...LEARNING, ...learning }
    this.random   = random.seeded(this.settings.seed)
    this.begin()
  }

  /**
   * Reads epsilon at the steps trained so far, along the schedule over the
   * budget.
   */
  get epsilon(): number {
    return epsilonAt(this.total, this.settings.budget, this.settings.schedule)
  }

  /**
   * Reads the row of values `state` holds, one to each button.
   */
  #row(state: number): Float32Array {
    return this.q.subarray(state * rooms.BUTTONS.length, (state + 1) * rooms.BUTTONS.length)
  }

  /**
   * Starts an episode outside Blue's door with no square seen but that one.
   */
  begin(): void {
    this.length           = 0
    this.seen             = new Uint8Array(town.townStates)
    this.state            = town.townDoor
    this.seen[this.state] = 1
  }

  /**
   * Chooses the button `state`'s row ranks first, at random among the ones tied
   * for first.
   */
  best(state: number): number {
    const row  = this.#row(state)
    const top  = Math.max(...row)
    const ties = [...row.keys()].filter(action => row[action] === top)
    return random.pickFrom(ties, this.random)
  }

  /**
   * Presses once, updates the table, and reports whether the press ended an
   * episode.
   */
  step(): boolean {
    const { alpha, cap, discount, novelty } = this.settings
    const action                            = this.random() < this.epsilon
                                            ? random.pickIndex(rooms.BUTTONS.length, this.random)
                                            : this.best(this.state)
    const { done, next, reward } = town.townStep(action, this.seen, this.state, novelty)
    const index                  = this.state * rooms.BUTTONS.length + action
    const upstream               = done ? 0 : this.value(next)
    const target                 = reward + discount * upstream
    const before                 = this.q[index]!
    this.q[index]                = before + alpha * (target - before)
    this.state                   = next
    this.length++
    this.total++
    if (!done && this.length < cap) return false
    this.lengths.push({ length: this.length, reached: done })
    this.begin()
    return true
  }

  /**
   * Reads the value of `state`'s best button.
   */
  value(state: number): number {
    return Math.max(...this.#row(state))
  }
}

/**
 * Reads epsilon at `step` of `steps` along `schedule`.
 */
export function epsilonAt(step: number, steps: number, schedule: Schedule = SCHEDULE): number {
  const { end, fraction, start } = schedule
  return start + (end - start) * Math.min(1, step / (fraction * steps))
}
