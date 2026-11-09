import { clamp } from '@vueuse/core'

import { round }       from '../drawing/plot.ts'
import { Player }      from '../game/player.ts'
import { seeded }      from '../game/random.ts'
import type * as rooms from '../game/rooms.ts'
import { SQUARE }      from '../game/screen.ts'
import { IDENTITY }    from '../identity/identity.ts'
import SETTINGS        from '../rendered/settings.json' with { type: 'json' }

/**
 * One step of a walk a window shows, the room, Blue's square and facing, and
 * the ball he chose.
 */
export interface Shown {
  at     : rooms.Square
  chosen : rooms.Square | null
  facing : rooms.Direction
  place  : rooms.Place
}

/**
 * The deep Q-network's replay memory as its settings declare it, the slots it
 * holds and the transitions one update reads from it.
 */
export const MEMORY = { batch: SETTINGS.agent.batch_size, capacity: SETTINGS.agent.capacity }

/**
 * The line of time the arcs land on, its width and height, its ends, and the
 * lane along its foot, beside the update's dot at its right end.
 */
export const LINE = { height: 150, lane: 136, left: 24, right: 616, top: 18, width: 640 } as const

/**
 * The updates the widget's slider steps through, the windows it shows, every
 * fourth of an update's reads from the newest, and the side of a window, the
 * three squares by three round Blue.
 */
export const UPDATES = 30
export const EVERY   = 4
export const WINDOW  = 3 * SQUARE

/**
 * The identity's motion, the milliseconds of one step every motion lasts a
 * whole number of and the curve it eases on.
 */
export const { curve: CURVE, duration: STEP } = IDENTITY.motion

/**
 * The milliseconds the widget rests on each update, long enough for every arc
 * to move in turn and settle.
 */
export const BEAT = (MEMORY.batch + 10) * STEP

/**
 * The steps ago each of the line's ticks marks, from the oldest replay memory
 * holds to the newest.
 */
export const TICKS: readonly number[] = [1, 0.75, 0.5, 0.25, 0].map(share => share * MEMORY.capacity)

/**
 * Reads where a step `age` steps ago lands along the line.
 */
export const xOf = (age: number): number => LINE.right - age / MEMORY.capacity * (LINE.right - LINE.left)

/**
 * Draws the arc from the update to the step `age` steps ago, rising higher the
 * older the step.
 */
export function arcOf(age: number): string {
  const x    = xOf(age)
  const lift = 12 + age / MEMORY.capacity * 90
  return `M${LINE.right} ${LINE.top} Q${round((x + LINE.right) / 2)} ${round(LINE.lane - lift)} ${round(x)} ${LINE.lane}`
}

/**
 * Reads the ages of the steps update `k` reads, drawn uniformly from replay
 * memory under a seed of its own, newest first.
 */
export function agesOf(k: number): number[] {
  const random = seeded(k * 31 + 11)
  return Array.from({ length: MEMORY.batch }, () => Math.floor(random() * MEMORY.capacity)).toSorted((a, b) => a - b)
}

/**
 * Reads the median of `ages`, sorted, the newest read, and the oldest.
 */
export function figuresOf(ages: readonly number[]): { median: number, newest: number, oldest: number } {
  const middle = (ages.length - 1) / 2
  return { median: Math.round((ages[Math.floor(middle)]! + ages[Math.ceil(middle)]!) / 2), newest: ages[0]!, oldest: ages.at(-1)! }
}

/**
 * Plays one episode of the model of the first rooms from `seed` and records
 * each step a window can show.
 */
export function walkOf(seed: number): Shown[] {
  const player = new Player({ seed })
  const snap   = (): Shown => {
    const { at, chosen, facing, place } = player.episode
    return { at, chosen, facing, place }
  }
  return [snap(), ...player.steps().map(() => snap())]
}

/**
 * The walks the windows show, one from each of the first seeds, standing in
 * for the environments the steps came from.
 */
export const WALKS: readonly Shown[][] = Array.from({ length: SETTINGS.agent.environments }, (_, i) => walkOf(i + 1))

/**
 * Reads the step the window of read `i`, `age` steps ago, shows.
 */
export function shownOf(age: number, i: number): Shown {
  const walk = WALKS[i % WALKS.length]!
  return walk[age % walk.length]!
}

/**
 * Reads where the window of the `n`th shown read, `age` steps ago, sits under
 * the line, as shares of the strip's width and height, the windows alternating
 * between two rows.
 */
export function windowAt(age: number, n: number): { left: number, top: number } {
  const x = clamp(xOf(age) - WINDOW / 2, 0, LINE.width - WINDOW)
  return { left: x / LINE.width, top: (n % 2) / 2 }
}
