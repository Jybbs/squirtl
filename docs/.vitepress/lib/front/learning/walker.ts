import * as sprites               from '../../drawing/sprites.ts'
import { frameFor }               from '../../game/actors.ts'
import type { Direction, Square } from '../../game/rooms.ts'
import * as screen                from '../../game/screen.ts'
import type { Footing }           from '../learning.ts'

/**
 * A bubble Blue shows over his head, the question bubble while the coin chooses
 * his next press and the shock bubble once Oak stops him.
 */
export type Emote = keyof typeof EMOTES

/**
 * The game's question and shock bubbles from pret/pokered's `gfx/emotes`, which
 * the town's script shows over Blue when Oak calls him.
 */
const EMOTES = {
  question: [
    '0001111111111000', '0013333333333100', '0131111111111310', '1311333333331131',
    '1313331111333131', '1313331111333131', '1311111333331131', '1311111331111131',
    '1311111111111131', '1311111331111131', '1311111331111131', '0131111111111310',
    '0013333333333100', '0001111133111000', '0000000131000000', '0000000110000000'
  ],
  shock: [
    '0001111111111000', '0013333333333100', '0131111111111310', '1311111331111131',
    '1311111331111131', '1311111331111131', '1311111331111131', '1311111331111131',
    '1311111111111131', '1311111331111131', '1311111331111131', '0131111111111310',
    '0013333333333100', '0001111133111000', '0000000131000000', '0000000110000000'
  ]
} as const satisfies Record<string, sprites.Grid>

/**
 * Each bubble split into the runs it draws, once as the module loads.
 */
const emoteRuns: Readonly<Record<Emote, readonly sprites.Run[]>> = {
  question : sprites.runsOf(EMOTES.question),
  shock    : sprites.runsOf(EMOTES.shock)
}

/**
 * One Blue of the walks, gliding from the square he stood on to the one his
 * latest press took him to, beside the way he faces and the bubble over him.
 */
export class Walker {
  bubble : Emote | null = 'question'
  facing : Direction    = 'down'

  readonly #from   : [number, number]
  readonly #stride : screen.Stride
  readonly #to     : [number, number]
  #span            = 0
  #t               = 1

  constructor(at: Square, stride: screen.Stride) {
    this.#from   = [...at]
    this.#stride = stride
    this.#to     = [...at]
  }

  /**
   * Reports whether Blue shows his walking frame, which he does through the
   * middle of a glide.
   */
  get stepping(): boolean {
    return this.#t > this.#stride[0] && this.#t < this.#stride[1]
  }

  /**
   * Reads the column Blue stands in, partway between two squares while he
   * glides.
   */
  get x(): number {
    return this.#from[0] + (this.#to[0] - this.#from[0]) * this.#t
  }

  /**
   * Reads the row Blue stands in, partway between two squares while he glides.
   */
  get y(): number {
    return this.#from[1] + (this.#to[1] - this.#from[1]) * this.#t
  }

  /**
   * Moves the glide `dt` milliseconds on and reports whether it ran this frame.
   */
  advance(dt: number): boolean {
    if (this.#t >= 1) return false
    this.#t = Math.min(1, this.#t + dt / this.#span)
    return true
  }

  /**
   * Paints Blue in `fills` with his top left at `x` and `y`, his walking frame
   * mid-glide, and his bubble a square above him.
   */
  paint(context: screen.Painter, fills: readonly string[], x: number, y: number): void {
    screen.paintSprite(context, frameFor('player', this.facing, this.stepping), x, y, fills)
    if (this.bubble) screen.paintRuns(context, emoteRuns[this.bubble], x, y - screen.SQUARE, fills)
  }

  /**
   * Starts a glide from where Blue stands to the square `footing` names over
   * `span` milliseconds, or sets him there at once where `span` is zero.
   *
   * He faces down under the shock bubble where `arrived` is set, and otherwise
   * faces the way he pressed, under the question bubble where the coin chooses
   * his next press.
   */
  place(footing: Footing, arrived: boolean, span: number): void {
    this.#from[0] = this.x
    this.#from[1] = this.y
    Object.assign(this.#to, footing.at)
    this.#span  = span
    this.#t     = span > 0 ? 0 : 1
    this.facing = arrived ? 'down' : footing.facing
    this.bubble = arrived ? 'shock' : footing.sure ? null : 'question'
  }
}
