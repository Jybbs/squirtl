import { type Stance, stancesOf } from '../game/gait.ts'
import { Learner }                from '../game/learner.ts'
import { pickIndex, seeded }      from '../game/random.ts'
import * as rooms                 from '../game/rooms.ts'
import * as town                  from '../game/town.ts'
import { counted, listed }        from '../widgets/numbers.ts'

/**
 * Blue's place after one press of a walk, the square he stands on, the way he
 * faces, and whether the table chooses his next press.
 */
export interface Footing {
  at     : rooms.Square
  facing : rooms.Direction
  sure   : boolean
}

/**
 * One walk from Blue's door with the table as it stood after `episodes`
 * episodes of training, the presses it took, whether it reached the north edge,
 * his place after each press from his door on, and the stances his gait runs
 * through on each frame of each press.
 */
export interface Moment {
  episodes : number
  presses  : number
  reached  : boolean
  stances  : readonly (readonly Stance[])[]
  steps    : readonly Footing[]
}

/**
 * A run of one walk's presses one chooser made, from the press `from` up to the
 * press `to`, the table's where `sure` is set and the coin's otherwise.
 */
export interface Stretch {
  from : number
  sure : boolean
  to   : number
}

/**
 * How the walks read the table, the seed of the coin that chooses where a
 * square holds no value, the episodes after which each walk reads it, and the
 * seed the table trains from.
 */
export interface Walking {
  coin    : number
  moments : readonly number[]
  seed    : number
}

/**
 * The walks the front page reads, the table trained from seed 3 and read after
 * 6, 30, 40, and 50 episodes, the coin drawing from seed 39.
 */
export const WALKING: Walking = { coin: 39, moments: [6, 30, 40, 50], seed: 3 }

/**
 * Lists the episodes after which each walk of `some` reads the table, as a
 * sentence lists them.
 */
function episodesOf(some: readonly Moment[]): string {
  return listed(some.map(moment => moment.episodes))
}

/**
 * Names the walks of `some` by their episodes beside what holds of them, `one`
 * where they hold one walk and `many` where they hold more, or nothing where
 * they hold none.
 */
function phrase(many: string, one: string, some: readonly Moment[]): string {
  if (some.length === 0) return ''
  if (some.length > 1) return `the walks after ${episodesOf(some)} episodes ${many}`
  return `the walk after ${episodesOf(some)} episodes ${one}`
}

/**
 * Walks once from Blue's door with the table `q`, pressing the direction each
 * square's row ranks first and, on a square holding no value, the one a coin
 * seeded with `coin` chooses, until he reaches the north edge or `cap` presses
 * have passed, a press other than the way he faces only turning him.
 */
function walkFrom(cap: number, coin: number, episodes: number, q: Float32Array): Moment {
  const walk  = town.playTown(cap, seeded(coin), (state, random) =>
    favored(q, state) ?? pickIndex(rooms.DIRECTIONS.length, random))
  const steps = walk.trail.map((state, press) => ({
    at     : town.squareOf(state),
    facing : walk.facings[press]!,
    sure   : favored(q, state) !== undefined
  }))
  return { episodes, presses: walk.steps, reached: walk.reached, stances: stancesOf(steps), steps }
}

/**
 * Says where every walk stands after `press` presses of the clock they share,
 * naming those that have reached the north edge, those stopped at the cap short
 * of it, and those still under way.
 */
export function clockText(moments: readonly Moment[], press: number): string {
  const ended = moments.filter(moment => press >= moment.presses)
  const parts = [
    phrase('have reached the north edge', 'has reached the north edge', ended.filter(walk => walk.reached)),
    phrase('have stopped short of it', 'has stopped short of it', ended.filter(walk => !walk.reached)),
    phrase('are still under way', 'is still under way', moments.filter(walk => press < walk.presses))
  ]
  return `At ${counted(press, 'press', 'presses')}, ${parts.filter(Boolean).join(', while ')}`
}

/**
 * Chooses the direction the row of `state` in the table `q` ranks first, the
 * first of those tied, where the row holds a value above zero for one.
 *
 * Returns:
 *   The direction's index among the buttons, or `undefined` where the row
 *   holds no value yet, so the table has no press to prefer.
 */
export function favored(q: Float32Array, state: number): number | undefined {
  const start = state * rooms.BUTTONS.length
  const row   = q.subarray(start, start + rooms.DIRECTIONS.length)
  const top   = Math.max(...row)
  return top > 0 ? row.indexOf(top) : undefined
}

/**
 * Counts the presses of the longest of `moments`, where the clock they share
 * ends.
 */
export function longestOf(moments: readonly Moment[]): number {
  return Math.max(...moments.map(moment => moment.presses))
}

/**
 * Names what the town's view shows, the walks from Blue's door after each
 * moment's episodes.
 */
export function sceneLabel(moments: readonly Moment[]): string {
  return `Pallet Town’s north half, where Blue walks from his door after ${episodesOf(moments)} `
       + 'episodes of training, every walk in its own hue on one clock of presses'
}

/**
 * Splits the presses of `moment` into the stretches each chooser made, the
 * table's where its square held a value and the coin's elsewhere.
 */
export function stretchesOf(moment: Moment): Stretch[] {
  const stretches: Stretch[] = []
  for (let press = 0; press < moment.presses; press++) {
    const sure = moment.steps[press]!.sure
    const last = stretches.at(-1)
    if (last?.sure === sure) last.to = press + 1
    else stretches.push({ from: press, sure, to: press + 1 })
  }
  return stretches
}

/**
 * Trains one table over the town and reads it after each moment's episodes,
 * walking once from Blue's door with the table as it stands then.
 */
export function walksOf(walking: Walking = WALKING): Moment[] {
  const learner = new Learner({ seed: walking.seed })
  return walking.moments.map(episodes => {
    while (learner.lengths.length < episodes) learner.step()
    return walkFrom(learner.settings.cap, walking.coin, episodes, learner.q)
  })
}
