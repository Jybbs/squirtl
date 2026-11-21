import { squareKey }    from '../../game/episode.ts'
import type * as rooms  from '../../game/rooms.ts'
import { FIRST, TRACE } from '../memory.ts'
import { PLAY }         from './play.ts'

/**
 * The count of the frame each square is first shown on, so its mark settles
 * over a fixed count of frames from it whether the episode plays or holds.
 */
const SEEN: ReadonlyMap<string, number> = (() => {
  const seen = new Map([[squareKey(TRACE[0]!.place, TRACE[0]!.at), 0]])
  let shown  = 0
  for (const frame of PLAY.steps.slice(1).flat()) {
    for (; shown < frame.row; shown++) {
      const row = TRACE[shown + 1]!
      const key = squareKey(row.place, row.at)
      if (FIRST.get(key) === shown + 1) seen.set(key, frame.clock)
    }
  }
  return seen
})()

/**
 * A square the episode reaches, the step first standing on it, and the count
 * of the frame it is first shown on.
 */
export interface Reached {
  at   : rooms.Square
  seen : number
  step : number
}

/**
 * Every square the episode reaches in each room.
 */
export const REACHED: Readonly<Record<rooms.Place, readonly Reached[]>> = Object.groupBy(
  TRACE.flatMap((row, n) => FIRST.get(squareKey(row.place, row.at)) === n
    ? [{ at: row.at, place: row.place, seen: SEEN.get(squareKey(row.place, row.at))!, step: n }]
    : []),
  each => each.place
) as Record<rooms.Place, Reached[]>
