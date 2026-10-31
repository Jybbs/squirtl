/**
 * A source of numbers drawn evenly from zero up to one, each call returning the
 * next.
 */
export type Random = () => number

/**
 * Picks one of `items` with one draw from `random`.
 */
export function pickFrom<T>(items: readonly T[], random: Random): T {
  return items[pickIndex(items.length, random)]!
}

/**
 * Picks an index below `count` with one draw from `random`.
 */
export function pickIndex(count: number, random: Random): number {
  return Math.floor(random() * count)
}

/**
 * Makes Mulberry32, a generator of 32-bit state, from `seed`, so one seed
 * always returns one sequence.
 *
 * The state sits in an `Int32Array`, whose element wraps each sum to a signed
 * 32-bit integer, the wrap Mulberry32's state takes.
 */
export function seeded(seed: number): Random {
  const state = Int32Array.of(seed)
  return () => {
    state[0]! += 0x6d2b79f5
    const s = state[0]!
    let t   = Math.imul(s ^ (s >>> 15), 1 | s)
    t       = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 2 ** 32
  }
}
