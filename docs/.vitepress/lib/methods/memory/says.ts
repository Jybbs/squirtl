import { type Term, squareKey } from '../../game/episode.ts'
import type * as rooms          from '../../game/rooms.ts'
import SETTINGS                 from '../../rendered/settings.json' with { type: 'json' }
import { count, fixed }         from '../../widgets/numbers.ts'
import { FIRST, FLAG_BITS, LAST, MAPS, ROOMS, type Row, TRACE, address, byte } from '../memory.ts'

/**
 * A run of a sentence and the mark whose hue it takes, none for plain words.
 */
export type Part = readonly [words: string, role: Role | null]

/**
 * The marks a run of a sentence names, the step, the bytes, or a term of the
 * reward.
 */
export type Role = 'bytes' | 'step' | Term

/**
 * What a step did to the bytes as the sentence beneath the map says it: the
 * step, what it did, what it paid, the words closing it, and the term it paid.
 */
export interface Say {
  did  : readonly Part[]
  paid : number
  step : string
  tail : readonly Part[]
  term : Term | null
}

/**
 * What the reward pays a square first reached.
 */
const NOVELTY = SETTINGS.reward.novelty

/**
 * Names a position as the three bytes `Position.read` takes.
 */
const position = (place: rooms.Place, at: rooms.Square): string => `(${byte(MAPS[place])}, ${byte(at[0])}, ${byte(at[1])})`

/**
 * Reads the term a step's payment counts toward, the goal's over a
 * milestone's over the position's.
 */
const termOf = (pay: Readonly<Record<Term, number>>): Term | null =>
  (['goal', 'milestone', 'novelty'] as const).find(term => pay[term] > 0) ?? null

/**
 * Says what step `n` of `trace` did to the bytes: a position reached for the
 * first time, each flag it set with its bit and byte, a press that only turned
 * Blue, or a square reached before, and what it paid.
 */
function sayOf(n: number, trace: readonly Row[] = TRACE): Say {
  const row  = trace[n]!
  const pos  = position(row.place, row.at)
  const paid = row.pay.novelty + row.pay.milestone + row.pay.goal
  const term = termOf(row.pay)
  const said = { paid, step: `Step ${count(n)}`, term }
  if (n === 0) return { ...said, did: [['stands on ', null], [pos, 'bytes'], [` in ${ROOMS[row.place]}`, null]], tail: [] }
  if (paid) {
    const set  = FLAG_BITS.filter(each => row.flags.has(each.flag) && !trace[n - 1]!.flags.has(each.flag))
    const did: Part[] = row.pay.novelty ? [['reaches ', null], [pos, 'bytes'], [' for the first time', 'novelty']] : []
    set.forEach((flag, k) => did.push([k ? ' and ' : row.pay.novelty ? ' and sets ' : 'sets ', null], [`${flag.name} (bit ${flag.bit} of ${address(flag.address)})`, flag.term]))
    return { ...said, did, tail: [[', paying ', null], [fixed(paid, 5), term], [term === 'goal' ? ', which ends the episode' : '', null]] }
  }
  if (row.turned) return { ...said, did: [[`turns Blue to face ${row.facing} on `, null], [pos, 'bytes'], [' without a step', null]], tail: [[', paying nothing', null]] }
  return { ...said, did: [['stands on ', null], [pos, 'bytes'], [', reached before', null]], tail: [[', paying nothing for the position', null]] }
}

export const SAYS: readonly Say[] = TRACE.map((_, n) => sayOf(n))

/**
 * Says whether the episode has reached the square `at` of `place` by step `n`,
 * and what the first step onto it pays.
 */
export function pointedSay(place: rooms.Place, at: rooms.Square, n: number): Say {
  const first   = FIRST.get(squareKey(place, at))
  const reached = first !== undefined && first <= n
  return {
    did  : [[position(place, at), 'bytes'], [` is ${reached ? '' : 'not '}reached by step ${count(n)}`, null]],
    paid : reached ? 0 : NOVELTY,
    step : `Step ${count(n)}`,
    tail : reached ? [[', so stepping onto it again pays nothing', null]] : [[', so the first step onto it pays ', null], [fixed(NOVELTY, 5), 'novelty']],
    term : reached ? null : 'novelty'
  }
}

/**
 * Lays out the whole sentence for a step, led by the step, or for a pointed
 * square, led by the square, and closed by a period.
 */
export const partsOf = (say: Say, pointed: boolean): Part[] =>
  [...(pointed ? [] : [[say.step, 'step'], [' ', null]] as Part[]), ...say.did, ...say.tail, ['.', null]]

/**
 * Joins the runs of a sentence into its words.
 */
export const textOf = (parts: readonly Part[]): string => parts.map(([words]) => words).join('')

/**
 * The longest sentence any step or pointed square takes, laid unseen under the
 * one shown so the line holds that height as the episode plays.
 */
export const LONGEST = [...SAYS.map(say => partsOf(say, false)), partsOf(pointedSay('pallet', [0, 0], LAST), true)]
  .map(parts => textOf(parts))
  .reduce((best, each) => each.length > best.length ? each : best, '')
