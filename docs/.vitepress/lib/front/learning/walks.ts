import { frameFor }               from '../../game/actors.ts'
import { PLAIN }                  from '../../game/palettes.ts'
import { OAK_LEADS }              from '../../game/rooms.ts'
import * as screen                from '../../game/screen.ts'
import { townStart }              from '../../game/town.ts'
import type { Hue }               from '../../identity/identity.ts'
import { type Moment, longestOf } from '../learning.ts'
import * as tints                 from './tints.ts'
import * as transition            from './transition.ts'
import { Walker }                 from './walker.ts'

/**
 * How the walks play: the milliseconds one press takes, the milliseconds one
 * cycle of a stack's crossfade takes and the colors it steps through, and the
 * opacity of every other Blue while one is picked out.
 */
export interface Play {
  blend      : number
  blendSteps : number
  dim        : number
  press      : number
}

/**
 * The canvas members the walks draw through.
 */
export type TownPainter = Pick<
  CanvasRenderingContext2D,
  'fillRect' | 'fillStyle' | 'globalAlpha' | 'imageSmoothingEnabled' | 'putImageData'
>

/**
 * How the walks play unless given otherwise.
 */
export const PLAY: Play = { blend: 1600, blendSteps: 24, dim: 0.16, press: 60 }

/**
 * The square Oak stops Blue from, the first one he leads him through.
 */
const oakAt = OAK_LEADS[1]

/**
 * Oak's frame as he stands below Blue looking up at him.
 */
const oakPose = frameFor('oak', 'up')

/**
 * Blue's walks from his door at each moment, set at one press of the clock they
 * share and drawn on one still view of the town.
 *
 * `set` places every Blue at a press, `advance` moves the glides, the
 * crossfade, and the transition on as time passes, and `draw` paints the town,
 * Oak once every walk has ended, and each Blue in his walk's hue, Blues on one
 * square drawn once and crossfading through their hues, and the double circle
 * closing over them. `encounter` starts the transition into a wild battle,
 * calling `covered` once the screen is black, and `calm` ends it.
 */
export class Walks {
  focus   : number | null = null
  grouped = false
  oak     = false
  palette : string        = PLAIN
  sprites = true
  tiles   = -1

  readonly blues   : readonly Walker[]
  readonly hues    : readonly Hue[]
  readonly longest : number
  readonly moments : readonly Moment[]
  readonly play    : Play
  readonly view    : transition.TownView

  readonly #blends : readonly (readonly (readonly string[])[])[]
  readonly #fills  : readonly (readonly string[])[]
  readonly #phases : transition.Phases
  readonly #xs     : Int32Array
  readonly #ys     : Int32Array
  #clock           = 0
  #covered         : (() => void) | undefined
  #elapsed         = -1

  constructor(
    moments : readonly Moment[],
    play    : Play                = PLAY,
    phases  : transition.Phases   = transition.battlePhases,
    view    : transition.TownView = transition.VIEW
  ) {
    this.blues   = moments.map(() => new Walker(townStart))
    this.hues    = tints.walkHuesOf(moments.length)
    this.longest = longestOf(moments)
    this.moments = moments
    this.play    = play
    this.view    = view
    this.#fills  = this.hues.map(hue => tints.fillsOf(hue))
    this.#blends = tints.blendsOf(this.#fills, play.blendSteps)
    this.#phases = phases
    this.#xs     = new Int32Array(moments.length)
    this.#ys     = new Int32Array(moments.length)
    this.set(0)
  }

  /**
   * Reports whether the transition into a wild battle is under way.
   */
  get closing(): boolean {
    return this.#elapsed >= 0
  }

  /**
   * Paints Blue `n` in `fills` at the pixel `#paintSprites` rounded his place
   * to.
   */
  #paintBlue(context: TownPainter, n: number, fills: readonly string[]): void {
    this.blues[n]!.paint(context, fills, this.#xs[n]!, this.#ys[n]! - this.view.lift)
  }

  /**
   * Paints every Blue in his walk's hue, the latest walk last so he stands in
   * front, and Blues on one pixel once as the latest of them stands, each shade
   * at the crossfade's current step through their hues.
   */
  #paintEvery(context: TownPainter): void {
    const step   = Math.floor(this.#clock / this.play.blend * this.play.blendSteps) % this.play.blendSteps
    let drawn    = 0
    this.grouped = false
    for (let n = 0; n < this.blues.length; n++) {
      if (drawn & (1 << n)) continue
      let stack = 1 << n
      for (let m = n + 1; m < this.blues.length; m++) {
        if (this.#xs[m] === this.#xs[n] && this.#ys[m] === this.#ys[n]) stack |= 1 << m
      }
      drawn |= stack
      if (stack === 1 << n) {
        this.#paintBlue(context, n, this.#fills[n]!)
        continue
      }
      this.grouped = true
      this.#paintBlue(context, 31 - Math.clz32(stack), this.#blends[stack]![step]!)
    }
  }

  /**
   * Paints every other Blue dimmed and then Blue `focus` at full strength, each
   * in his own walk's hue.
   */
  #paintPicked(context: TownPainter, focus: number): void {
    this.grouped        = false
    context.globalAlpha = this.play.dim
    for (let n = 0; n < this.blues.length; n++) if (n !== focus) this.#paintBlue(context, n, this.#fills[n]!)
    context.globalAlpha = 1
    this.#paintBlue(context, focus, this.#fills[focus]!)
  }

  /**
   * Rounds each Blue's place to the view's pixels, then paints Oak where every
   * walk has ended and the Blues over him.
   */
  #paintSprites(context: TownPainter): void {
    const { lift, x, y } = this.view
    for (let n = 0; n < this.blues.length; n++) {
      this.#xs[n] = Math.round((this.blues[n]!.x - x) * screen.SQUARE)
      this.#ys[n] = Math.round((this.blues[n]!.y - y) * screen.SQUARE)
    }
    if (this.oak) {
      const left = Math.round((oakAt[0] - x) * screen.SQUARE)
      const top  = Math.round((oakAt[1] - y) * screen.SQUARE) - lift
      screen.paintSprite(context, oakPose, left, top)
    }
    if (this.focus === null) this.#paintEvery(context)
    else this.#paintPicked(context, this.focus)
  }

  /**
   * Moves every glide, the crossfade, and any transition `dt` milliseconds on,
   * and reports whether anything still moves, a stack still crossfading
   * counting as moving.
   */
  advance(dt: number): boolean {
    let moving = false
    for (const blue of this.blues) moving = blue.advance(dt) || moving
    this.#clock = (this.#clock + dt) % this.play.blend
    if (this.#elapsed < 0) return moving || this.grouped
    this.#elapsed += dt
    const t       = this.#elapsed
    this.palette  = transition.paletteAt(t, this.#phases)
    this.tiles    = transition.tileStepAt(t, this.#phases)
    this.sprites  = transition.spritesAt(t, this.#phases)
    if (this.#covered && t >= this.#phases.circle) {
      const covered = this.#covered
      this.#covered = undefined
      covered()
    }
    if (t >= this.#phases.end) this.calm()
    return true
  }

  /**
   * Ends any transition at once and returns the screen to the town's own
   * palette.
   */
  calm(): void {
    this.#covered = undefined
    this.#elapsed = -1
    this.palette  = PLAIN
    this.sprites  = true
    this.tiles    = -1
  }

  /**
   * Paints the town in the current palette and everyone standing in it, then
   * the tiles the double circle has blacked so far, once `town` holds the
   * town's view.
   */
  draw(context: TownPainter, town: transition.Town): void {
    const background = town.palettes.get(this.palette)
    if (!background) return
    context.imageSmoothingEnabled = false
    context.globalAlpha           = 1
    context.putImageData(background, 0, 0)
    if (this.sprites) this.#paintSprites(context)
    if (this.tiles >= 0) transition.paintCircle(context, this.tiles, town)
  }

  /**
   * Starts the transition into a wild battle over the town, calling `covered`
   * once while the screen is black.
   */
  encounter(covered: () => void): void {
    this.#covered = covered
    this.#elapsed = 0
  }

  /**
   * Places every Blue where his walk stands after `press` presses, gliding
   * there over `span` milliseconds, and where `span` is set leaves a Blue whose
   * walk has already ended where he stands.
   */
  set(press: number, span = 0): void {
    for (let n = 0; n < this.moments.length; n++) {
      const moment = this.moments[n]!
      if (span > 0 && press > moment.presses) continue
      const footing = moment.steps[Math.min(press, moment.presses)]!
      const arrived = moment.reached && press >= moment.presses
      this.blues[n]!.place(footing, arrived, span, moment.stances[press - 1] ?? null)
    }
    this.oak = press >= this.longest
  }
}
