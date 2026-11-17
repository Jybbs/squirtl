import { Episode }                        from '../../game/episode.ts'
import type { RoomImages }                from '../../game/images.ts'
import { GameScreen, type ScreenPainter } from '../../game/screen.ts'
import { SEARCH, pathOf }                 from '../search.ts'
import { type Shown, TIMING }             from './moments.ts'

/**
 * The screen one copy of the game shows, its rollout pressed into its own
 * episode a press at a time, Blue gliding through each, and every other change
 * replayed from the bedroom along the tree, fading in from the backdrop where
 * the copy has moved to its winner's saved state.
 */
export class CopyScreen {
  readonly #episode = new Episode()
  readonly #screen  : GameScreen
  #from             = 0
  #node             : number | null = 0
  #pressed          = 0

  constructor(images: RoomImages) {
    this.#screen = new GameScreen(this.#episode, images)
  }

  /**
   * Moves the screen `dt` milliseconds through its glide and its fade, and
   * reports whether either still runs.
   */
  advance(dt: number): boolean {
    return this.#screen.advance(dt)
  }

  /**
   * Draws the screen into `context`, a canvas the Game Boy's screen's size.
   */
  draw(context: ScreenPainter): void {
    this.#screen.draw(context)
  }

  /**
   * Sets the screen to show `shown`, gliding where it is the next press of the
   * rollout the screen shows, or the first from the node the screen stands on,
   * and otherwise replaying the episode from the bedroom.
   */
  show(shown: Shown): void {
    const { copy, from, pressed, state } = shown
    if (from === this.#node && pressed === 1) {
      this.#from    = from
      this.#pressed = 0
    }
    if (from === this.#from && pressed === this.#pressed) return
    this.#node = pressed === 0 ? from : pressed === copy.presses.length ? copy.node : null
    if (from === this.#from && pressed === this.#pressed + 1) {
      this.#episode.press(copy.presses[this.#pressed]!)
      this.#pressed = pressed
      this.#screen.follow(TIMING.press)
      return
    }
    this.#episode.reset()
    const replay = [...pathOf(SEARCH.nodes, from), ...copy.presses.slice(0, pressed)]
    for (const press of replay) this.#episode.press(press)
    this.#from    = from
    this.#pressed = pressed
    this.#screen.snap(state === 'moved')
  }
}
