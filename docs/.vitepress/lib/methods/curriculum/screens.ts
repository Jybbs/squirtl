import { Episode }                    from '../../game/episode.ts'
import type { RoomImages }            from '../../game/images.ts'
import { CENTER, GameScreen, SQUARE } from '../../game/screen.ts'
import { IDENTITY, hueHex, roleHue }  from '../../identity/identity.ts'
import { type Segment, TIMING }       from '../curriculum.ts'
import { TRACE }                      from '../memory.ts'

/**
 * Where a segment's screen stands while a batch plays: the steps of the
 * recording it has replayed, and whether it shows the recording, gray, or the
 * agent at its start, in color.
 */
export interface Lane {
  phase : 'agent' | 'recording'
  step  : number
}

/**
 * The part of the Game Boy's screen a lane's screen shows, 112 by 100 of its
 * pixels around Blue, so a narrow screen shows him larger than the whole
 * screen scaled down would.
 */
export const LENS = { height: 100, left: 16, top: 18, width: 112 } as const

/**
 * Reads where a segment's screen stands `t` milliseconds into a batch whose
 * episode starts at `start`: the recording replayed in gray over the replay's
 * milliseconds, then the agent standing at the start in color, at once for an
 * episode starting in the bedroom.
 */
export function laneAt(start: number, t: number): Lane {
  return t < TIMING.replay && start > 0
       ? { phase: 'recording', step: Math.floor(t / TIMING.replay * start) }
       : { phase: 'agent', step: start }
}

/**
 * The screen one segment's lane carries, the recording replayed press by press
 * into its own episode, drawn around Blue with the goal's square ringed in the
 * goal's hue wherever it is in view.
 */
export class LaneScreen {
  readonly #episode = new Episode()
  readonly #goal    : (typeof TRACE)[number]
  readonly #ring    : string
  readonly #screen  : GameScreen

  constructor(segment: Segment, images: RoomImages) {
    this.#goal   = TRACE[segment.end + 1]!
    this.#ring   = hueHex(roleHue(segment.term))
    this.#screen = new GameScreen(this.#episode, images)
  }

  /**
   * Draws the recording after `step` presses into `context`, a canvas the
   * lens's size, replaying from the bedroom where the step lies behind the one
   * the screen last showed.
   */
  draw(context: CanvasRenderingContext2D, step: number): void {
    if (step < this.#episode.steps) this.#episode.reset()
    while (this.#episode.steps < step) this.#episode.press(TRACE[this.#episode.steps + 1]!.press!)
    this.#screen.snap()
    context.setTransform(1, 0, 0, 1, -LENS.left, -LENS.top)
    this.#screen.draw(context)
    context.setTransform(1, 0, 0, 1, 0, 0)
    const { at, place } = this.#screen.view
    if (this.#goal.place !== place) return
    const x = (this.#goal.at[0] - at[0] + CENTER) * SQUARE - LENS.left
    const y = (this.#goal.at[1] - at[1] + CENTER) * SQUARE - LENS.top
    const line = IDENTITY.lengths.borders.ring
    context.strokeStyle = this.#ring
    context.lineWidth   = line
    context.strokeRect(x + line / 2, y + line / 2, SQUARE - line, SQUARE - line)
  }
}
