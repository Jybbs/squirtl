import { clamp } from '@vueuse/core'

import type { Term }    from '../game/episode.ts'
import type { Flag }    from '../game/flags.ts'
import { seeded }          from '../game/random.ts'
import type * as rooms     from '../game/rooms.ts'
import SETTINGS            from '../rendered/settings.json' with { type: 'json' }
import { count }           from '../widgets/numbers.ts'
import { type Row, TRACE } from './memory.ts'

/**
 * The settings of the curriculum the drawing plays, each as
 * `CurriculumSettings` declares it: the least and most a window moves back
 * and forward as multiples of its span, the share reaching the bedroom that
 * solves a segment, the episodes a share is read over, the share that moves a
 * window back, and the steps a window spans.
 */
export interface Curriculum {
  back       : readonly [number, number]
  completion : number
  forward    : readonly [number, number]
  recent     : number
  required   : number
  window     : number
}

/**
 * One segment of the recording, the step whose press first sets its flags,
 * the goal the episodes from it reach a step later, the words naming that
 * goal, and the term of the reward its flags pay.
 */
export interface Segment {
  end  : number
  tag  : string
  term : Term
}

/**
 * What a batch shows of one segment: the start of the episode it shows, the
 * farthest back of those whose outcome matches what the batch did to the
 * window, and whether the segment was solved before the batch, after which its
 * episodes start in the bedroom.
 */
export interface Shown {
  solved : boolean
  start  : number
}

/**
 * The places of the recording in the order Blue reaches them, each named as
 * the game names it, with the first and last steps he stands there.
 */
export interface Stretch {
  first : number
  last  : number
  name  : string
  place : rooms.Place
}

/**
 * The words naming the goal each flag ends a segment at, a segment taking the
 * last flag its press sets.
 */
const TAGS: Readonly<Record<Flag, string>> = {
  appeared : 'Oak stops Blue',
  asked    : 'Oak asks Blue to choose',
  followed : 'Blue follows Oak in',
  starter  : 'Blue takes a starter'
}

/**
 * The settings the drawing plays, the defaults the package declares.
 */
export const CURRICULUM: Curriculum = {
  back       : [SETTINGS.curriculum.back[0]!, SETTINGS.curriculum.back[1]!],
  completion : SETTINGS.curriculum.completion,
  forward    : [SETTINGS.curriculum.forward[0]!, SETTINGS.curriculum.forward[1]!],
  recent     : SETTINGS.curriculum.recent,
  required   : SETTINGS.curriculum.required,
  window     : SETTINGS.curriculum.window
}

/**
 * The milliseconds a batch replays the recording up to each start over, and
 * the milliseconds it then rests on the starts before the next batch.
 */
export const TIMING = { replay: 1100, rest: 2200 } as const

/**
 * The places of the recording, each named as the game names it.
 */
const NAMES: Readonly<Record<rooms.Place, string>> = {
  bedroom : 'Bedroom',
  house   : 'House',
  lab     : 'Oak’s Lab',
  pallet  : 'Pallet Town'
}

/**
 * Splits `trace` into segments, each ending at the step whose press first sets
 * one or more of the flags the reward pays, as the demonstration's `ends` lists
 * them. Row n of the trace holds the state after n presses, so the press that
 * first shows a flag in row n is step n - 1.
 */
function segmentsOf(trace: readonly Row[] = TRACE): Segment[] {
  const seen = new Set<Flag>()
  return trace.flatMap((row, n) => {
    const fresh = [...row.flags].filter(flag => !seen.has(flag))
    for (const flag of fresh) seen.add(flag)
    return fresh.length > 0 ? [{ end: n - 1, tag: TAGS[fresh.at(-1)!], term: fresh.includes('starter') ? 'starter' : 'milestone' }] : []
  })
}

export const SEGMENTS = segmentsOf()

/**
 * The share of episodes from a start that reach their goal `left` steps on at
 * batch `batch`, falling with the steps left and rising as training goes on, a
 * made-up model of an agent improving.
 */
export const odds = (left: number, batch: number): number => clamp(0.5 + (8 + 5 * batch - left) / 10, 0.02, 0.99)

/**
 * Plays a seeded run of the curriculum until every segment is solved, each
 * unsolved window taking `recent` episodes a batch from starts drawn uniformly
 * across it, each reaching its goal at `odds`. Each window then moves as
 * `Curriculum.attempted` moves it: one in the bedroom whose share reaches
 * `completion` is solved, a share reaching `required` moves it back by a
 * uniform draw from `back` times its span, and a smaller one forward by a draw
 * from `forward`, never past the bedroom or the segment's end.
 *
 * Returns:
 *   What each batch shows of each segment.
 */
export function runOf(curriculum: Curriculum = CURRICULUM, segments: readonly Segment[] = SEGMENTS, seed = 34): Shown[][] {
  const random  = seeded(seed)
  const draw    = ([low, high]: readonly [number, number]) => low + random() * (high - low)
  const windows = segments.map(segment => ({ latest: segment.end, solved: false }))
  const batches: Shown[][] = []

  for (let b = 0; !windows.every(window => window.solved); b++) {
    batches.push(segments.map((segment, k) => {
      const window = windows[k]!
      const low    = Math.max(0, window.latest - curriculum.window)
      if (window.solved) return { solved: true, start: 0 }
      const tries = Array.from({ length: curriculum.recent }, () => {
        const start = Math.round(low + random() * (window.latest - low))
        return { start, won: random() < odds(segment.end - start, b) }
      })
      const share = tries.filter(each => each.won).length / tries.length
      const won   = share >= curriculum.required
      if (window.latest === 0 && share >= curriculum.completion) window.solved = true
      else if (won) window.latest = Math.max(0, window.latest - Math.round(draw(curriculum.back) * curriculum.window))
      else window.latest = Math.min(segment.end, window.latest + Math.round(draw(curriculum.forward) * curriculum.window))
      const shown = tries.filter(each => each.won === won).toSorted((left, right) => left.start - right.start)[0] ?? tries[0]!
      return { solved: false, start: shown.start }
    }))
  }

  return batches
}

export const RUN = runOf()

export const BATCHES = RUN.length

export const LAST = TRACE.length - 1

/**
 * The places of the recording, each with the steps Blue stands in it.
 */
export const STRETCHES: readonly Stretch[] = (Object.keys(NAMES) as rooms.Place[])
  .map(place => {
    const steps = TRACE.flatMap((row, n) => row.place === place ? [n] : [])
    return { first: steps[0]!, last: steps.at(-1)!, name: NAMES[place], place }
  })
  .toSorted((left, right) => left.first - right.first)

/**
 * The share of the way from the bedroom to the end of the recording a step
 * stands at.
 */
export const along = (step: number): number => step / (LAST + 1)

/**
 * Names batch `b` as the readout prints it.
 */
export const batchName = (b: number): string => `Batch ${count(b + 1)} of ${count(BATCHES)}`

/**
 * Describes batch `b` for a screen reader, with the segments solved by its end.
 */
export function describe(b: number): string {
  const solved = RUN[b + 1]?.filter(each => each.solved).length ?? SEGMENTS.length
  return `${batchName(b)}, ${count(solved)} of ${count(SEGMENTS.length)} segments solved`
}

/**
 * Writes how far before its goal the episode segment `k` shows at batch `b`
 * starts.
 */
export function farOf(b: number, k: number): string {
  const { solved, start } = RUN[b]![k]!
  if (solved) return 'Solved from the bedroom'
  return start ? `${count(SEGMENTS[k]!.end + 1 - start)} presses before it` : 'From the bedroom'
}
