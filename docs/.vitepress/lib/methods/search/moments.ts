import type { Term }                      from '../../game/episode.ts'
import { count }                          from '../../widgets/numbers.ts'
import { type Copy, LAST, SEARCH, SIZES } from '../search.ts'

/**
 * The figures over the copies at a moment: the iteration, or the
 * demonstration's length once a copy has chosen a starter, the presses the
 * copies have spent, and the tree's nodes and saved states.
 */
export interface Figures {
  demonstration : boolean
  iteration     : string
  nodes         : number
  saved         : number
  spent         : number
}

/**
 * A copy as the drawing shows it at a moment: the node it stands on and the
 * presses of its rollout it has made from there, its mark, the term of the
 * flag its rollout set, where it shows one, the total its lineage holds, and
 * its uncertainty once its rollout ends.
 */
export interface Shown {
  copy        : Copy
  from        : number
  pressed     : number
  state       : State
  term        : Term | null
  total       : number
  uncertainty : number | null
}

/**
 * The mark a copy carries: none while its rollout plays, the ring of its
 * group's winner, the cross of a dead copy, a live copy that lost, and a copy
 * that has moved to its winner's saved state.
 */
type State = '' | 'dead' | 'lost' | 'moved' | 'win'

/**
 * The moments of an iteration after its presses, once every rollout has ended
 * and each group's winner shows, and once every other copy has moved to it.
 */
export const ENDED = SIZES.presses + 1
export const MOVED = SIZES.presses + 2
/**
 * The milliseconds of each press, of the pause after a rollout while each
 * group's winner shows, and into that pause at which every other copy moves
 * to it.
 */
export const TIMING = { move: 500, press: 80, select: 900 } as const
/**
 * The milliseconds the rollouts of one iteration take, and the whole of it.
 */
export const ROLLING   = SIZES.presses * TIMING.press
export const ITERATION = ROLLING + TIMING.select

/**
 * Counts the slider's position `at`: the iteration of all of them, or the
 * demonstration's presses at the last position.
 */
function countOf(at: number): string {
  return at === LAST ? `${count(SEARCH.demonstration.length)} presses` : `${count(at + 1)} of ${count(LAST)}`
}

/**
 * Reads the mark a copy carries once its rollout has ended, the ring where it
 * is its group's winner.
 */
function stateOf(copy: Copy, winner: boolean, last: boolean): State {
  if (winner) return 'win'
  if (last) return ''
  return copy.dead ? 'dead' : 'lost'
}

/**
 * Describes the slider's position `at` for a screen reader.
 */
export function describe(at: number): string {
  return `${at === LAST ? 'The demonstration,' : 'Iteration'} ${countOf(at)}`
}

/**
 * Reads the figures at `moment` of the slider's position `at`, each count
 * standing at the end of the last iteration that has ended.
 */
export function figuresOf(at: number, moment: number): Figures {
  const ended = at === LAST ? LAST : at + Number(moment >= ENDED)
  const done  = SEARCH.iterations[ended - 1]
  return {
    demonstration : at === LAST,
    iteration     : countOf(at),
    nodes         : done?.nodes ?? 1,
    saved         : done?.saved ?? 1,
    spent         : done?.spent ?? 0
  }
}

/**
 * Reads the moment of an iteration `t` milliseconds in: the presses each
 * rollout has made, one every `TIMING.press` milliseconds from the first at
 * once, then `ENDED` once the rollouts end, and `MOVED` `TIMING.move`
 * milliseconds later.
 */
export function momentOf(t: number): number {
  if (t >= ROLLING + TIMING.move) return MOVED
  return t >= ROLLING ? ENDED : Math.floor(t / TIMING.press) + 1
}

/**
 * Reads each copy as it shows at `moment` of the slider's position `at`, by
 * group. A copy has made as many presses of its rollout as the moment names
 * until its rollout ends, then carries its mark and its uncertainty, and once
 * the moment reaches `MOVED`, every copy off its group's next node has moved
 * there. The demonstration shows each copy at the end of the last iteration,
 * the copy that chose a starter ringed.
 */
export function shownOf(at: number, moment: number): Shown[][] {
  const last       = at === LAST
  const ended      = last || moment >= ENDED
  const moved      = !last && moment >= MOVED
  const { groups } = SEARCH.iterations[last ? LAST - 1 : at]!

  return groups.map((group, g) => group.copies.map((copy, slot): Shown => {
    if (moved && copy.node !== group.next) {
      return {
        copy        : copy,
        from        : group.next,
        pressed     : 0,
        state       : 'moved',
        term        : null,
        total       : SEARCH.nodes[group.next]!.total,
        uncertainty : copy.uncertainty
      }
    }
    const pressed = ended ? copy.presses.length : Math.min(moment, copy.presses.length)
    const winner  = last ? SEARCH.found.group === g && SEARCH.found.slot === slot : group.winner === slot
    return {
      copy        : copy,
      from        : copy.start,
      pressed     : pressed,
      state       : ended ? stateOf(copy, winner, last) : '',
      term        : pressed === copy.presses.length ? copy.term : null,
      total       : copy.totals[pressed]!,
      uncertainty : ended ? copy.uncertainty : null
    }
  }))
}
