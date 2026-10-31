import EVENTS     from '../rendered/events.json' with { type: 'json' }
import SETTINGS   from '../rendered/settings.json' with { type: 'json' }
import * as rooms from './rooms.ts'

/**
 * The bounds an episode keeps, the presses it runs to before it stops and what
 * each term of the reward pays.
 */
export interface EpisodeSettings {
  limit : number
  pay   : Readonly<Record<Term, number>>
}

/**
 * One event flag the network reads, the flag the model of the game sets for
 * it, its name on a widget, and the term of the reward the step first setting
 * it pays.
 */
export interface EventFlag {
  flag : Flag
  name : string
  term : Term
}

/**
 * A moment in the game an event flag marks, each milestone's and the starter's.
 */
export type Flag = (typeof FLAGS)[keyof typeof FLAGS]['flag']

/**
 * Where Oak stands while he leads Blue, and the way he faces.
 */
export interface Leader {
  at     : rooms.Square
  facing : rooms.Direction
  place  : rooms.Place
}

/**
 * One payment a press earns, its amount and the term it pays.
 */
export interface Paid {
  pay  : number
  term : Term
}

/**
 * A term of the reward, as the settings name it.
 */
export type Term = keyof typeof SETTINGS.reward

/**
 * The bounds every episode keeps unless given others, the episode's limit and
 * the reward's payments the settings declare.
 */
export const EPISODE: EpisodeSettings = {
  limit : SETTINGS.environment.max_episode_steps,
  pay   : SETTINGS.reward
}

/**
 * The flag the model of the game sets for each event flag the network reads,
 * beside the name a widget gives it, under the name the package's `Event`
 * gives the flag.
 */
const FLAGS = {
  EVENT_FOLLOWED_OAK_INTO_LAB   : { flag: 'followed', name: 'Followed Oak' },
  EVENT_GOT_STARTER             : { flag: 'starter', name: 'Got the starter' },
  EVENT_OAK_APPEARED_IN_PALLET  : { flag: 'appeared', name: 'Oak appeared' },
  EVENT_OAK_ASKED_TO_CHOOSE_MON : { flag: 'asked', name: 'Oak asked' }
} as const

/**
 * Where Blue wakes, the square pret/pokered's `NewGameWarp` puts him on in his
 * bedroom.
 */
const START = { at: [3, 6], facing: 'down', place: 'bedroom' } as const

/**
 * The squares Blue walks behind Oak, each beside its room, from the north edge
 * of Pallet Town to the table in the lab.
 */
const leadScript: readonly (readonly [rooms.Place, rooms.Square])[] = [
  ...rooms.OAK_LEADS.map(at => ['pallet', at] as const),
  ...rooms.LAB_ENTRY.map(at => ['lab', at] as const)
]

/**
 * The event flags the network reads, in the order the package's `Event`
 * declares them, each beside the term of the reward the step first setting it
 * pays.
 */
export const eventFlags: readonly EventFlag[] = EVENTS.map(event =>
  Object.assign({ term: event.term as Term }, FLAGS[event.name as keyof typeof FLAGS]))

/**
 * The flags of the milestones on the way to the starter, those whose events pay
 * a milestone.
 */
export const milestones: readonly Flag[] = eventFlags
  .filter(each => each.term === 'milestone')
  .map(each => each.flag)

/**
 * The term of the reward each flag pays the first time a step sets it.
 */
const pays = Object.fromEntries(eventFlags.map(each => [each.flag, each.term])) as Readonly<
  Record<Flag, Term>
>

/**
 * One episode of the model of the first rooms, from Blue waking in his bedroom
 * until he chooses the starter or the episode reaches its limit, and what each
 * press in it pays.
 *
 * Blue stands `at` a square of `place` facing `facing`, and `lastStop` holds
 * the direction he last stopped in, none until his first direction press.
 * `pressed` holds the latest button pressed, and `turned` whether that press
 * only turned him.
 * `reached` holds the key of every square he has stood on, and `shares` what
 * each term has paid. Once Oak stops him, `script` holds the squares he walks
 * behind Oak, and every press walks him to the next while `leader` holds where
 * Oak stands.
 */
export class Episode {
  at!         : rooms.Square
  chosen!     : rooms.Square | null
  facing!     : rooms.Direction
  flags!      : Set<Flag>
  lastStop!   : rooms.Direction | null
  leader!     : Leader | null
  place!      : rooms.Place
  pressed!    : rooms.Button | null
  reached!    : Set<string>
  script!     : (readonly [rooms.Place, rooms.Square])[]
  shares!     : Record<Term, number>
  steps!      : number
  terminated! : boolean
  turned!     : boolean

  readonly settings: EpisodeSettings

  constructor(settings: EpisodeSettings = EPISODE) {
    this.settings = settings
    this.reset()
  }

  /**
   * Reports whether the episode has ended, at the starter or at its limit.
   */
  get done(): boolean {
    return this.terminated || this.steps >= this.settings.limit
  }

  /**
   * Sums what every term has paid so far.
   */
  get total(): number {
    return Object.values(this.shares).reduce((sum, share) => sum + share, 0)
  }

  /**
   * Walks Blue to the next square behind Oak, facing the way he steps, and pays
   * the milestones of following Oak in and of Oak asking him to choose once he
   * reaches the table.
   */
  #advance(): Paid[] {
    const [place, at] = this.script.shift()!
    const next        = this.script[0]
    const leads       = next?.[0] === place
    this.facing       = place === this.place ? rooms.heading(this.at, at) : 'up'
    this.lastStop     = this.facing
    this.leader       = leads ? { at: next[1], facing: rooms.heading(at, next[1]), place } : null
    const paid        = this.#arrive(place, at)
    if (this.script.length > 0) return paid
    this.facing = this.lastStop = 'up'
    return [...paid, ...this.#flag('followed'), ...this.#flag('asked')]
  }

  /**
   * Stands Blue on `at` in `place`, paying a new position where he has not
   * stood there before.
   */
  #arrive(place: rooms.Place, at: rooms.Square): Paid[] {
    this.place = place
    this.at    = at
    const key  = this.key()
    if (this.reached.has(key)) return []
    this.reached.add(key)
    this.shares.novelty += this.settings.pay.novelty
    return [{ pay: this.settings.pay.novelty, term: 'novelty' }]
  }

  /**
   * Sets `flag`, paying the term its event pays the first time, the starter's
   * flag ending the episode.
   */
  #flag(flag: Flag): Paid[] {
    if (this.flags.has(flag)) return []
    this.flags.add(flag)
    const term = pays[flag]
    const pay  = this.settings.pay[term]
    this.shares[term] += pay
    if (flag === 'starter') this.terminated = true
    return [{ pay, term }]
  }

  /**
   * Reads the key `reached` holds for the square Blue stands on.
   */
  key(): string {
    return squareKey(this.place, this.at)
  }

  /**
   * Presses `button` once, counting the step, and reads what the press pays.
   *
   * A press while Oak leads walks Blue to the next square behind him whatever
   * the button. A direction other than the one he last stopped in only turns
   * him, as pret/pokered's `OverworldLoop` sends it through
   * `.holdIntermediateDirectionLoop`, so a reset's first direction press turns
   * him. One he last stopped in steps him where the square is walkable, takes
   * him through a warp or off a door mat, or leaves him where it is blocked. A
   * chooses the starter where he faces a Poké Ball, and B moves nothing.
   */
  press(button: rooms.Button): Paid[] {
    if (this.done) return []
    this.steps++
    this.pressed = button
    this.turned  = false
    if (this.script.length > 0) return this.#advance()
    if (button === 'a') {
      const ball = rooms.ballAhead(this, this.facing)
      if (!ball) return []
      this.chosen = ball
      return this.#flag('starter')
    }
    if (button === 'b') return []
    this.facing = button
    if (button !== this.lastStop) {
      this.lastStop = button
      this.turned   = true
      return []
    }
    const to   = rooms.neighbor(this.at, button)
    const warp = rooms.warpOf(this, button)
    if (warp) return this.#arrive(warp.to, warp.arrive)
    if (!rooms.passable(to, this.place)) return []
    const paid = this.#arrive(this.place, to)
    if (!oakStops(this, to)) return paid
    this.script = [...leadScript]
    this.leader = { at: rooms.OAK_LEADS[1], facing: 'down', place: 'pallet' }
    return [...paid, ...this.#flag('appeared')]
  }

  /**
   * Starts the episode again from the bedroom, every count and flag cleared.
   */
  reset(): void {
    this.at         = START.at
    this.chosen     = null
    this.facing     = START.facing
    this.flags      = new Set()
    this.lastStop   = null
    this.leader     = null
    this.place      = START.place
    this.pressed    = null
    this.script     = []
    this.shares     = { milestone: 0, novelty: 0, starter: 0 }
    this.steps      = 0
    this.terminated = false
    this.turned     = false
    this.reached    = new Set([this.key()])
  }
}

/**
 * Reports whether a step onto `at` in the room `episode` stands in has Oak stop
 * Blue, which a step onto Pallet Town's north edge does until Oak has appeared
 * once.
 */
function oakStops(episode: Pick<Episode, 'flags' | 'place'>, at: rooms.Square): boolean {
  return episode.place === 'pallet' && at[1] <= rooms.NORTH_EDGE && !episode.flags.has('appeared')
}

/**
 * Writes the key an episode's `reached` holds for the square `at` in `place`.
 */
export function squareKey(place: rooms.Place, at: rooms.Square): string {
  return `${place}:${at[0]},${at[1]}`
}
