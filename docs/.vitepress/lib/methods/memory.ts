import { type Flag, type Leader, type Term, eventFlags, squareKey } from '../game/episode.ts'
import { Player }      from '../game/player.ts'
import type * as rooms from '../game/rooms.ts'
import SYMBOLS         from '../rendered/symbols.json' with { type: 'json' }
import { count }       from '../widgets/numbers.ts'

/**
 * One flag the reward reads, beside the byte of the game's memory holding it
 * and its bit in that byte.
 */
export interface FlagBit {
  address : number
  bit     : number
  flag    : Flag
  name    : string
  term    : Term
}

/**
 * The episode after one step: Blue's square, room, and facing, whether the
 * press only turned him, the flags set, where Oak stands while he leads, the
 * Poké Ball chosen, what each term paid, the press, whether Oak's script
 * walked Blue rather than the press, and the bytes the reward reads.
 */
export interface Row {
  at       : rooms.Square
  bytes    : ReadonlyMap<number, number>
  chosen   : rooms.Square | null
  facing   : rooms.Direction
  flags    : ReadonlySet<Flag>
  leader   : Leader | null
  pay      : Readonly<Record<Term, number>>
  place    : rooms.Place
  press    : rooms.Button | null
  scripted : boolean
  turned   : boolean
}

/**
 * The addresses of the bytes the reward reads, as `Symbol` declares them.
 */
export const ADDRESS = {
  flags : SYMBOLS.W_EVENT_FLAGS,
  map   : SYMBOLS.W_CUR_MAP,
  x     : SYMBOLS.W_X_COORD,
  y     : SYMBOLS.W_Y_COORD
} as const

/**
 * The map numbers pret/pokered's `constants/map_constants.asm` gives the rooms
 * an episode crosses, and the words naming each room.
 */
export const MAPS: Readonly<Record<rooms.Place, number>> = { bedroom: 0x26, house: 0x25, lab: 0x28, pallet: 0x00 }

export const ROOMS: Readonly<Record<rooms.Place, string>> = {
  bedroom : 'the bedroom',
  house   : 'downstairs',
  lab     : 'Oak’s lab',
  pallet  : 'Pallet Town'
}

/**
 * Each flag the reward reads at bit `index % 8` of the byte `index // 8` past
 * `wEventFlags`, as pret/pokered's `CheckEvent` reads it.
 */
export const FLAG_BITS: readonly FlagBit[] = eventFlags.map(each =>
  Object.assign({ address: ADDRESS.flags + (each.index >> 3), bit: each.index & 7 }, each))

/**
 * The second byte of `wEventFlags` the widget shows, which holds every flag
 * but the first.
 */
export const SECOND = ADDRESS.flags + 4

/**
 * Writes `value` as the two hexadecimal digits of a byte, and as the digits of
 * an address.
 */
export const byte = (value: number): string => value.toString(16).toUpperCase().padStart(2, '0')

export const address = (value: number): string => value.toString(16).toUpperCase()

/**
 * Reads the five bytes the reward reads after a step. pret/pokered's
 * `OaksLabFollowedOakScript` sets `EVENT_FOLLOWED_OAK_INTO_LAB_2`, bit 0 of the
 * second byte, beside `EVENT_FOLLOWED_OAK_INTO_LAB`, so that bit turns on with
 * it though the reward never reads it.
 */
export function bytesOf(place: rooms.Place, at: rooms.Square, flags: ReadonlySet<Flag>): Map<number, number> {
  const bytes = new Map([
    [ADDRESS.map, MAPS[place]], [ADDRESS.y, at[1]], [ADDRESS.x, at[0]], [ADDRESS.flags, 0], [SECOND, flags.has('followed') ? 1 : 0]
  ])
  for (const each of FLAG_BITS) if (flags.has(each.flag)) bytes.set(each.address, bytes.get(each.address)! | 1 << each.bit)
  return bytes
}

/**
 * Plays an episode of the model of the first rooms through `player`, a row a
 * step from the reset.
 */
export function traceOf(player = new Player()): Row[] {
  const rows: Row[] = []
  const snap = (paid: readonly { pay: number, term: Term }[], scripted: boolean) => {
    const { at, chosen, facing, flags, leader, place, turned } = player.episode
    const pay = { goal: 0, milestone: 0, novelty: 0 }
    for (const each of paid) pay[each.term] += each.pay
    rows.push({
      at, bytes: bytesOf(place, at, flags), chosen, facing, flags: new Set(flags), leader: leader && { ...leader },
      pay, place, press: player.button, scripted, turned
    })
  }
  snap([], false)
  while (!player.done) {
    const scripted = player.episode.script.length > 0
    snap(player.next(), scripted)
  }
  return rows
}

export const TRACE = traceOf()

export const LAST = TRACE.length - 1

/**
 * The step each square of every room is first reached on, keyed as the
 * episode keys a square.
 */
export const FIRST: ReadonlyMap<string, number> = TRACE.reduce(
  (first, row, n) => first.has(squareKey(row.place, row.at)) ? first : first.set(squareKey(row.place, row.at), n),
  new Map<string, number>()
)

/**
 * The square each step leaves as the newest the episode has reached, the last
 * one a step first stood on.
 */
export const NEWEST: readonly Row[] = TRACE.reduce<Row[]>((newest, row, n) => {
  newest.push(FIRST.get(squareKey(row.place, row.at)) === n ? row : newest.at(-1)!)
  return newest
}, [])

/**
 * Describes step `n` for a screen reader.
 */
export const describe = (n: number): string => `Step ${count(n)} of ${count(LAST)}`
