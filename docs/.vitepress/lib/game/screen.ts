import WORLD                  from '../art/world.json' with { type: 'json' }
import * as sprites           from '../drawing/sprites.ts'
import * as identity          from '../identity/identity.ts'
import * as actors            from './actors.ts'
import type { Episode }       from './episode.ts'
import type { RoomImages }    from './images.ts'
import type { Place, Square } from './rooms.ts'

/**
 * The runs one frame splits into, as drawn and mirrored.
 */
type FrameRuns = readonly [readonly sprites.Run[], readonly sprites.Run[]]

/**
 * How the screen moves, the milliseconds a change of room fades in over and
 * the share of a step's glide over which Blue shows his walking frame.
 */
export interface Glide {
  fade   : number
  stride : Stride
}

/**
 * The canvas members a sprite and the battle transition's double circle draw
 * through.
 */
export type Painter = Pick<CanvasRenderingContext2D, 'fillRect' | 'fillStyle'>

/**
 * The canvas members the game screen draws through.
 */
export type ScreenPainter = Pick<
  CanvasRenderingContext2D,
  'drawImage' | 'fillRect' | 'fillStyle' | 'globalAlpha' | 'imageSmoothingEnabled'
>

/**
 * The shares of a step's glide over which Blue shows his walking frame, from
 * its start to its end.
 */
export type Stride = readonly [start: number, end: number]

/**
 * The square the screen centers on and its room, which a glide moves through
 * the fractions between two squares.
 */
export interface View {
  at    : [x: number, y: number]
  place : Place
}

/**
 * The squares from the screen's left and top edges to Blue's, who stands at
 * column 4 and row 4 of the ten columns and nine rows it shows.
 */
const CENTER = 4

/**
 * The pixels a sprite stands above its square, a Poké Ball's and everyone
 * else's.
 */
export const LIFT = { ball: 2, person: 4 }

/**
 * The Game Boy's screen in pixels.
 */
export const SCREEN = { height: 144, width: 160 }

/**
 * The pixels on each side of one square of a room.
 */
export const SQUARE = 16

/**
 * The share of a step's glide over which Blue shows his walking frame, from its
 * start to its end.
 */
export const STRIDE: Stride = [0.2, 0.8]

/**
 * The glide every screen keeps unless given another.
 */
export const GLIDE: Glide = { fade: 320, stride: STRIDE }

/**
 * The fill around a room's image and of the fade between rooms.
 */
const backdrop = identity.hexOf('deep')

/**
 * Every frame of every sprite the identity declares split into its runs, as
 * drawn and mirrored, once as the module loads.
 */
const spriteRuns: ReadonlyMap<sprites.Grid, FrameRuns> = new Map(
  Object.values(identity.IDENTITY.sprites)
    .flatMap(sprite => sprite.frames)
    .map(grid => [grid, [sprites.runsOf(grid), sprites.runsOf(grid, true)]] as const)
)

/**
 * The pixels from the screen's left and top edges to Blue's square.
 */
const middle = CENTER * SQUARE

/**
 * The Game Boy's screen showing one episode, Blue at its center, the room
 * around him, and everyone standing in it.
 *
 * `follow` starts a glide of the view from where it stands to Blue's square,
 * `advance` moves it on as time passes, and `snap` sets it on Blue's square at
 * once. A step to a neighboring square glides with Blue showing his walking
 * frame mid-step, a farther move jumps, and a change of room fades in from the
 * backdrop.
 */
export class GameScreen {
  leaderAt : Square | undefined
  stepping = false
  veil     = 0

  readonly episode : Episode
  readonly view    : View

  readonly #from       : [number, number] = [0, 0]
  readonly #glide      : Glide
  readonly #images     : RoomImages
  readonly #leader     : [number, number] = [0, 0]
  readonly #leaderFrom : [number, number] = [0, 0]
  #leadFrom            : Square | undefined
  #leadTo              : Square | undefined
  #near                = false
  #span                = 0
  #t                   = 1
  #to                  : Square

  constructor(episode: Episode, images: RoomImages, glide: Glide = GLIDE) {
    this.episode  = episode
    this.leaderAt = episode.leader?.at
    this.view     = { at: [...episode.at], place: episode.place }
    this.#glide   = glide
    this.#images  = images
    this.#to      = episode.at
  }

  /**
   * Sets the view and Oak `t` of the way through the glide, Blue walking
   * mid-step where the glide covers one square.
   */
  #place(t: number): void {
    this.#t       = t
    this.stepping = this.#near && t > this.#glide.stride[0] && t < this.#glide.stride[1]
    lerpInto(this.view.at, this.#near ? this.#from : this.#to, this.#to, t)
    this.leaderAt = t < 1 && this.#leadFrom && this.#leadTo
                  ? lerpInto(this.#leader, this.#leadFrom, this.#leadTo, t)
                  : this.#leadTo
  }

  /**
   * Moves the view `dt` milliseconds further through its glide and its fade,
   * and reports whether either still runs.
   */
  advance(dt: number): boolean {
    this.veil = Math.max(0, this.veil - dt / this.#glide.fade)
    if (this.#t < 1) this.#place(this.#span > 0 ? Math.min(1, this.#t + dt / this.#span) : 1)
    return this.#t < 1 || this.veil > 0
  }

  /**
   * Draws the room around the view, everyone standing in it, Blue at the
   * center, and the fade over them.
   */
  draw(context: ScreenPainter): void {
    const { at, place }           = this.view
    const { height, width }       = SCREEN
    const { pad }                 = WORLD[place]
    const left                    = Math.round((at[0] - CENTER + pad) * SQUARE)
    const top                     = Math.round((at[1] - CENTER + pad) * SQUARE)
    context.imageSmoothingEnabled = false
    context.globalAlpha           = 1
    context.fillStyle             = backdrop
    context.fillRect(0, 0, width, height)
    context.drawImage(this.#images.image(place), left, top, width, height, 0, 0, width, height)
    for (const actor of actors.actorsOf(this.episode, this.leaderAt, this.stepping)) {
      const pose = actors.frameFor(actor.name, actor.facing, actor.stepping)
      const x    = Math.round((actor.at[0] - at[0] + CENTER) * SQUARE)
      const y    = Math.round((actor.at[1] - at[1] + CENTER) * SQUARE)
      paintSprite(context, pose, x, y - (actor.name === 'ball' ? LIFT.ball : LIFT.person))
    }
    const blue = actors.frameFor('player', this.episode.facing, this.stepping)
    paintSprite(context, blue, middle, middle - LIFT.person)
    if (this.veil <= 0) return
    context.globalAlpha = this.veil
    context.fillStyle   = backdrop
    context.fillRect(0, 0, width, height)
    context.globalAlpha = 1
  }

  /**
   * Starts a glide of the view from where it stands to Blue's square over
   * `span` milliseconds, Oak gliding beside him, or a fade where Blue has
   * changed rooms.
   */
  follow(span: number): void {
    const { at, leader, place } = this.episode
    if (place !== this.view.place) {
      this.snap(true)
      return
    }
    this.#near     = Math.abs(this.view.at[0] - at[0]) + Math.abs(this.view.at[1] - at[1]) === 1
    this.#leadFrom = this.leaderAt && Object.assign(this.#leaderFrom, this.leaderAt)
    this.#leadTo   = leader?.at
    this.#span     = span
    this.#t        = 0
    this.#to       = at
    Object.assign(this.#from, this.view.at)
  }

  /**
   * Sets the view on Blue's square and Oak on his at once, fading in from the
   * backdrop where `fade` is set.
   */
  snap(fade = false): void {
    const { at, leader, place } = this.episode
    Object.assign(this.view.at, at)
    this.view.place = place
    this.leaderAt   = leader?.at
    this.stepping   = false
    this.veil       = fade ? 1 : 0
    this.#t         = 1
  }
}

/**
 * Writes the point `t` of the way from `from` to `to` into `target`, `to`
 * itself once `t` reaches 1, and reads `target` back.
 */
function lerpInto(target: [number, number], from: Square, to: Square, t: number): [number, number] {
  target[0] = t < 1 ? from[0] + (to[0] - from[0]) * t : to[0]
  target[1] = t < 1 ? from[1] + (to[1] - from[1]) * t : to[1]
  return target
}

/**
 * Draws `runs` in `fills` with their top left at `x` and `y`, one canvas pixel
 * to each of theirs, every run as one rectangle snapped to whole pixels.
 */
export function paintRuns(
  context : Painter,
  runs    : readonly sprites.Run[],
  x       : number,
  y       : number,
  fills   : readonly string[] = identity.spriteShades
): void {
  for (const { shade, width, x: dx, y: dy } of runs) {
    context.fillStyle = fills[shade]!
    context.fillRect(Math.round(x + dx), Math.round(y + dy), width, 1)
  }
}

/**
 * Draws the frame of `pose` in `fills`, the Game Boy's shades unless given
 * others, with its top left at `x` and `y`, mirrored where the pose is.
 */
export function paintSprite(
  context : Painter,
  pose    : actors.Pose,
  x       : number,
  y       : number,
  fills   : readonly string[] = identity.spriteShades
): void {
  paintRuns(context, runsFor(pose.grid, pose.mirrored), x, y, fills)
}

/**
 * Reads the runs `grid` splits into, mirrored where `mirrored` is set, from the
 * runs split once for the identity's sprites, or splits them for any other
 * frame.
 */
export function runsFor(grid: sprites.Grid, mirrored = false): readonly sprites.Run[] {
  return spriteRuns.get(grid)?.[Number(mirrored)] ?? sprites.runsOf(grid, mirrored)
}
