import { Episode, type Paid }            from './episode.ts'
import { type Random, pickFrom, seeded } from './random.ts'
import * as rooms                        from './rooms.ts'

/**
 * How a player presses, the seed its draws start from.
 */
export interface Playing {
  seed: number
}

/**
 * The square each room's walk to the lab ends on: the bedroom's stairs, the
 * house's door mat, and the square of Pallet Town's north edge where Oak's path
 * starts.
 */
export const GOALS: Readonly<Record<Exclude<rooms.Place, 'lab'>, rooms.Square>> = {
  bedroom : rooms.RULES.bedroom.warps[0].at,
  house   : rooms.RULES.house.exits[0].at,
  pallet  : rooms.OAK_LEADS[0]
}

/**
 * The seed every player takes unless given another.
 */
export const PLAYING: Playing = { seed: 11 }

/**
 * The presses the agent's stand-in makes at random before it walks the shortest
 * way.
 */
export const WANDER = 90

/**
 * The square below Squirtle's Poké Ball, the middle of the three on Oak's
 * table, where the agent's stand-in turns up and presses A.
 */
export const pickAt = rooms.neighbor(rooms.RULES.lab.balls[1], 'down')

/**
 * One episode of the model of the first rooms, pressed by the agent's stand-in
 * or by a reader holding a button, and played again from the bedroom once it
 * ends.
 *
 * A reader's press sets `queued` for the next press alone, and a button the
 * reader holds sets `held` for every press until it is let go, while `button`
 * and `paid` hold the last press and what it paid.
 */
export class Player {
  button  : rooms.Button | null = null
  held    : rooms.Button | null = null
  paid    : Paid[]              = []
  queued  : rooms.Button | null = null
  random! : Random

  readonly episode : Episode = new Episode()
  readonly seed    : number

  constructor(playing: Partial<Playing> = {}) {
    const { seed } = { ...PLAYING, ...playing }
    this.seed      = seed
    this.reset()
  }

  /**
   * Reports whether the episode has ended.
   */
  get done(): boolean {
    return this.episode.done
  }

  /**
   * Chooses the next press, a reader's queued or held button outside Oak's walk
   * and the agent's stand-in's press otherwise.
   */
  choose(): rooms.Button {
    const { episode, queued } = this
    const walking             = episode.script.length > 0
    this.queued               = null
    if (queued && !walking) return queued
    if (this.held && !walking) return this.held
    return autoPress(episode, this.random)
  }

  /**
   * Presses until the episode ends.
   */
  finish(): void {
    this.playTo()
  }

  /**
   * Chooses the next press and makes it, reading what it pays.
   */
  next(): Paid[] {
    this.button = this.choose()
    this.paid   = this.episode.press(this.button)
    return this.paid
  }

  /**
   * Presses until the episode has run `step` presses or has ended.
   */
  playTo(step = Number.POSITIVE_INFINITY): void {
    while (!this.done && this.episode.steps < step) this.next()
  }

  /**
   * Starts the episode again from the bedroom with the draws from its seed.
   */
  reset(): void {
    this.episode.reset()
    this.button = null
    this.held   = null
    this.paid   = []
    this.queued = null
    this.random = seeded(this.seed)
  }

  /**
   * Plays the episode again from the bedroom up to the step `step`, or to its
   * end where it ends sooner.
   */
  seek(step: number): void {
    this.reset()
    this.playTo(step)
  }
}

/**
 * Chooses the agent's stand-in's press, B while Oak leads, a random button for
 * the first `wander` presses, and after them the first step of the shortest
 * walk to the room's goal, A once Blue faces Squirtle's Poké Ball, and a random
 * direction where no walk reaches the goal.
 */
export function autoPress(episode: Episode, random: Random, wander = WANDER): rooms.Button {
  if (episode.script.length > 0) return 'b'
  if (episode.steps < wander) return pickFrom(rooms.BUTTONS, random)
  if (episode.place === 'lab' && rooms.same(episode.at, pickAt)) return episode.facing === 'up' ? 'a' : 'up'
  if (episode.place === 'house' && rooms.same(episode.at, GOALS.house)) return 'down'
  const goal = episode.place === 'lab' ? pickAt : GOALS[episode.place]
  return rooms.routeMoves(episode, goal)[0] ?? pickFrom(rooms.DIRECTIONS, random)
}
