import { Episode, type Term }            from '../game/episode.ts'
import { type Random, pickFrom, seeded } from '../game/random.ts'
import { BUTTONS, type Button }          from '../game/rooms.ts'
import SETTINGS                          from '../rendered/settings.json' with { type: 'json' }
import { count }                         from '../widgets/numbers.ts'

/**
 * One copy of the game in one iteration: the button it holds, the presses its
 * rollout made from the node it started on, the total `Progress` paid its
 * lineage after each of them, the node the rollout added to the tree, none for
 * a dead copy, and the uncertainty of its last square. `term` names the term
 * of the flag its last press set, where it set one.
 */
export interface Copy {
  dead        : boolean
  held        : Button
  node        : number | null
  presses     : readonly Button[]
  start       : number
  term        : Term | null
  totals      : readonly number[]
  uncertainty : number
}

/**
 * One group in one iteration: its copies, the slot of its winner, none where
 * every copy died, and the node every copy moves to once the iteration ends.
 */
interface Group {
  copies : readonly Copy[]
  next   : number
  winner : number | null
}

/**
 * One iteration of the search: its groups, whether both moved to the better
 * winner, and the presses spent, the tree's nodes, and its saved states once
 * it ends.
 */
interface Iteration {
  groups : readonly Group[]
  nodes  : number
  saved  : number
  spent  : number
  synced : boolean
}

/**
 * A node of the tree, its parent, none for the root, the presses of the
 * rollout reaching it, and the total `Progress` pays its lineage.
 */
interface Node {
  parent  : number | null
  presses : readonly Button[]
  total   : number
}

/**
 * A rollout once it ends, before the tree takes it, beside the square it ends
 * on.
 */
type Roll = Omit<Copy, 'node' | 'uncertainty'> & { last: string }

/**
 * A search as the drawing plays it: every iteration, every node, the copy
 * that set the starter's flag, and the presses from the bedroom to its node.
 */
export interface Search {
  demonstration : readonly Button[]
  found         : { group: number, slot: number }
  iterations    : readonly Iteration[]
  nodes         : readonly Node[]
}

/**
 * The sizes a search runs at: the chance of a random press, its groups, the
 * copies each group holds, the most presses a rollout makes, the seed its
 * draws start from, and the iterations between moves of every group to the
 * better winner.
 */
export interface Sizes {
  epsilon   : number
  groups    : number
  particles : number
  presses   : number
  seed      : number
  sync      : number
}

/**
 * A search under way from the bedroom: the tree's nodes, the random source its
 * rollouts draw from, how often it has stood on each square, the saved states,
 * the presses spent, and the node each group starts its next iteration from.
 */
class Run {
  readonly nodes   : Node[] = [{ parent: null, presses: [], total: 0 }]
  readonly #random : Random
  readonly #sizes  : Sizes
  readonly #visits = new Map<string, number>()
  #saved           = new Set([0])
  #spent           = 0
  #starts          : number[]

  constructor(sizes: Sizes) {
    this.#random = seeded(sizes.seed)
    this.#sizes  = sizes
    this.#starts = Array.from({ length: sizes.groups }, () => 0)
  }

  /**
   * Plays iteration `n` of the search, a rollout for every copy, moving each
   * group to its next node, both to the better one every `sync` iterations,
   * and dropping each saved state on no group's lineage.
   */
  iterate(n: number): Iteration {
    const { nodes }           = this
    const { particles, sync } = this.#sizes
    const totalOf             = (group: Group): number => nodes[group.next]!.total

    const played = this.#starts.map(start => Array.from({ length: particles }, () => this.#roll(start)))
    for (const { last, presses } of played.flat()) {
      this.#visits.set(last, (this.#visits.get(last) ?? 0) + 1)
      this.#spent += presses.length
    }
    const groups = played.map((rolls, g) => this.#group(rolls, this.#starts[g]!))
    const synced = n % sync === 0
    const best   = groups.reduce((top, group) => totalOf(group) > totalOf(top) ? group : top).next
    if (synced) for (const group of groups) group.next = best
    this.#starts = groups.map(group => group.next)
    const kept   = new Set(this.#starts.flatMap(start => lineageOf(nodes, start)))
    this.#saved  = new Set([...this.#saved, ...this.#starts].filter(node => kept.has(node)))
    return { groups, nodes: nodes.length, saved: this.#saved.size, spent: this.#spent, synced }
  }

  /**
   * Adds the node a live rollout reached to the tree, returning its index, and
   * adds nothing for a dead one.
   */
  #add(roll: Omit<Roll, 'last'>): number | null {
    if (roll.dead) return null
    return this.nodes.push({ parent: roll.start, presses: roll.presses, total: rankOf(roll) }) - 1
  }

  /**
   * Adds each copy of a group that survived `rolls` to the tree and keeps its
   * winner, the live copy whose lineage pays the most and then the one whose
   * last square the search has stood on least. Its next node is the winner's,
   * or the parent of the one it began on where every copy died.
   */
  #group(rolls: readonly Roll[], start: number): Group {
    const { nodes } = this
    const copies    = rolls.map(({ last, ...roll }): Copy => ({
      ...roll,
      node        : this.#add(roll),
      uncertainty : 1 / Math.sqrt(this.#visits.get(last)!)
    }))
    const winner = copies.flatMap((copy, slot) => copy.dead ? [] : [slot])
      .toSorted((left, right) => byRank(copies[left]!, copies[right]!))
      .at(0)
    const next   = winner === undefined ? nodes[start]!.parent ?? 0 : copies[winner]!.node!
    return { copies, next, winner: winner ?? null }
  }

  /**
   * Plays one rollout from `start`, holding one button drawn for it and taking
   * a random one at `epsilon` a press, until it has made `presses` presses or
   * a press has set a flag the reward pays, as the search halts a rollout. A
   * new square leaves it playing, and it is dead where it ends on the screen,
   * the square, and the total it began on.
   */
  #roll(start: number): Roll {
    const { epsilon, presses: most } = this.#sizes
    const random                     = this.#random
    const episode                    = new Episode()
    for (const press of pathOf(this.nodes, start)) episode.press(press)
    const before  = screenOf(episode)
    const held    = pickFrom(BUTTONS, random)
    const presses = [] as Button[]
    const totals  = [episode.total]
    let term: Term | null = null

    while (presses.length < most && term === null && !episode.done) {
      const press = random() < epsilon ? pickFrom(BUTTONS, random) : held
      const paid  = episode.press(press).filter(each => each.term !== 'novelty')
      presses.push(press)
      totals.push(episode.total)
      term = paid.at(-1)?.term ?? null
    }

    return { dead: screenOf(episode) === before, held, last: episode.key(), presses, start, term, totals }
  }
}

/**
 * The search's sizes in the drawing, made up beside the chance of a random
 * press the package declares.
 */
export const SIZES: Sizes = {
  epsilon   : SETTINGS.search.epsilon,
  groups    : 2,
  particles : 4,
  presses   : 10,
  seed      : 21,
  sync      : 4
}
/**
 * The search the drawing plays, and the slider's last position, which shows
 * the demonstration once the iterations end.
 */
export const SEARCH = searchOf()
export const LAST   = SEARCH.iterations.length

/**
 * Orders two copies by the total their lineage pays, the higher first, and
 * then by uncertainty, the higher first.
 */
function byRank(left: Copy, right: Copy): number {
  return rankOf(right) - rankOf(left) || right.uncertainty - left.uncertainty
}

/**
 * Finds the copy of `iteration` that set the starter's flag, where one did.
 */
function foundIn(iteration: Iteration): Search['found'] | undefined {
  const slots = iteration.groups.map(({ copies }) => copies.findIndex(({ term }) => term === 'goal'))
  const group = slots.findIndex(slot => slot >= 0)
  return group < 0 ? undefined : { group, slot: slots[group]! }
}

/**
 * Lists `node` and every node above it up to the root.
 */
function lineageOf(nodes: readonly Node[], node: number): number[] {
  const lineage = [] as number[]
  for (let at: number | null = node; at !== null; at = nodes[at]!.parent) lineage.push(at)
  return lineage
}

/**
 * Reads the total `Progress` pays a copy's lineage once its rollout ends.
 */
function rankOf(copy: Pick<Copy, 'totals'>): number {
  return copy.totals.at(-1)!
}

/**
 * Reads Blue's square, the text the screen shows, and the total paid, which a
 * dead rollout ends on as it began.
 */
function screenOf(episode: Episode): string {
  const { at, chosen, place, script, speech } = episode
  return `${place}:${at}:${speech}:${script.length}:${chosen}:${episode.total}`
}

/**
 * Lists the presses from the bedroom to `node` along the tree.
 */
export function pathOf(nodes: readonly Node[], node: number): Button[] {
  return lineageOf(nodes, node)
    .toReversed()
    .flatMap(at => nodes[at]!.presses)
}

/**
 * Plays a seeded search from the bedroom on the model of the first rooms, an
 * iteration at a time until a copy sets the starter's flag, whose presses from
 * the bedroom are the demonstration.
 *
 * Raises:
 *   Error: Where no copy sets the flag within `cap` iterations.
 */
export function searchOf(sizes: Sizes = SIZES, cap = 200): Search {
  const run        = new Run(sizes)
  const iterations = [] as Iteration[]

  while (iterations.length < cap) {
    const iteration = run.iterate(iterations.length + 1)
    const found     = foundIn(iteration)
    iterations.push(iteration)
    if (found) {
      const { node } = iteration.groups[found.group]!.copies[found.slot]!
      return { demonstration: pathOf(run.nodes, node!), found, iterations, nodes: run.nodes }
    }
  }
  throw new Error(`The search sets no starter's flag within ${count(cap)} iterations`)
}
