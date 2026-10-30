import WORLD                             from '../art/world.json' with { type: 'json' }
import { eventFlags, squareKey }         from '../game/episode.ts'
import { PLAYING, Player, type Playing } from '../game/player.ts'
import { SCREEN }                        from '../game/screen.ts'
import * as identity                     from '../identity/identity.ts'
import SETTINGS                          from '../rendered/settings.json' with { type: 'json' }

/**
 * The shape of what the network reads, each frame's height and width, the side
 * of the grid of squares reached, and the frames stacked, beside the luma from
 * 0 to 1 at or below which a pixel of the screen takes each next darker of
 * PyBoy's grays.
 */
export interface Observing {
  frame  : { height: number, width: number }
  grid   : number
  levels : readonly number[]
  stack  : number
}

/**
 * The four grays PyBoy draws a cartridge for the original Game Boy in, from the
 * lightest of the game's shades to the darkest, whose red channel the network
 * reads.
 */
const GRAYS: readonly number[] = [255, 153, 85, 0]

/**
 * The tokens of the identity's neutrals each of PyBoy's grays draws in, from
 * its white to its black.
 */
const GRAY_TONES: readonly identity.Token[] = ['ground', 'muted', 'quiet', 'dark']

/**
 * The shape the settings give the observation, beside the luma levels that
 * split the four shades the rooms are drawn in, Athens Gray, Denim Pale, Denim
 * Mid, and Denim Deep, into PyBoy's white, light gray, dark gray, and black.
 */
export const OBSERVING: Observing = {
  frame  : { height: SETTINGS.environment.frame_shape[0]!, width: SETTINGS.environment.frame_shape[1]! },
  grid   : SETTINGS.environment.grid_size,
  levels : [0.85, 0.62, 0.36],
  stack  : SETTINGS.environment.frame_stack
}

/**
 * The pixel Blue's own square of the grid draws, in the agent's hue.
 */
const agent = pixelOf(identity.rgbOf(identity.IDENTITY.marks[identity.roleHue('agent')].light))

/**
 * The pixel each gray from 0 to 255 draws, PyBoy's four grays falling on the
 * identity's neutrals and every gray between two of them on the line joining
 * their colors.
 */
const ramp = rampOf(GRAY_TONES.map(token => identity.rgbOf(identity.hexOf(token))))

/**
 * Reads the gray PyBoy draws the pixel of `screen` at `index` in, the gray of
 * the first luma level the pixel's luma rises above, or black where it rises
 * above none.
 */
function grayOf(screen: ArrayLike<number>, index: number, levels: readonly number[]): number {
  const luma = (0.299 * screen[index]! + 0.587 * screen[index + 1]! + 0.114 * screen[index + 2]!) / 255
  let shade  = 0
  while (shade < levels.length && luma <= levels[shade]!) shade++
  return GRAYS[shade]!
}

/**
 * Packs the opaque pixel of the color `rgb` into the one word its four bytes
 * fill, in the byte order of a canvas's image data.
 */
function pixelOf(rgb: readonly number[]): number {
  return new Uint32Array(Uint8ClampedArray.of(...rgb, 255).buffer)[0]!
}

/**
 * Builds the pixel of each gray from 0 to 255 from the color `tones` gives each
 * of PyBoy's grays, mixing the two tones on either side of a gray by how near
 * it sits to each.
 */
function rampOf(tones: readonly (readonly number[])[]): Uint32Array {
  return Uint32Array.from({ length: 256 }, (_, gray) => {
    const upper = Math.max(0, GRAYS.findIndex(each => each <= gray) - 1)
    const share = (GRAYS[upper]! - gray) / (GRAYS[upper]! - GRAYS[upper + 1]!)
    return pixelOf(identity.mixRgb(tones[upper]!, tones[upper + 1]!, share))
  })
}

/**
 * Counts the bytes each entry of the observation holds, one a pixel of each
 * frame, one a square of the grid, and one a flag.
 */
export function bytesOf(observing: Observing = OBSERVING): Record<'flags' | 'frames' | 'grid', number> {
  const { frame, grid, stack } = observing
  return { flags: eventFlags.length, frames: stack * frame.height * frame.width, grid: grid * grid }
}

/**
 * Writes the gray frame `frame` into `pixels`, four bytes a pixel, each gray in
 * the color the identity's neutrals give it.
 */
export function paintFrame(frame: Uint8Array, pixels: Uint8ClampedArray): void {
  const words = new Uint32Array(pixels.buffer, pixels.byteOffset, frame.length)
  for (let i = 0; i < frame.length; i++) words[i] = ramp[frame[i]!]!
}

/**
 * Writes the grid of squares reached `grid` into `pixels`, four bytes a square,
 * a square reached in PyBoy's white and one not reached in its black, each in
 * the color the identity's neutrals give it, and Blue's own square at the
 * center in the agent's hue.
 */
export function paintGrid(grid: Uint8Array, pixels: Uint8ClampedArray, side = OBSERVING.grid): void {
  const words  = new Uint32Array(pixels.buffer, pixels.byteOffset, grid.length)
  const center = Math.floor(side / 2)
  for (let i = 0; i < grid.length; i++) words[i] = ramp[grid[i]! * 255]!
  words[center * side + center] = agent
}

/**
 * Shrinks the Game Boy's screen `screen`, four bytes a pixel, into the gray
 * frame `frame`, turning each pixel to PyBoy's gray for it and setting each
 * cell to the mean of the block of pixels it covers, in integers rounding a
 * half up, as the environment's `ShrinkObservation` does.
 */
export function shrink(screen: ArrayLike<number>, frame: Uint8Array, observing: Observing = OBSERVING): void {
  const { height, width } = observing.frame
  const across            = SCREEN.width / width
  const down              = SCREEN.height / height
  const cells             = across * down
  for (let cell = 0; cell < frame.length; cell++) {
    const row    = Math.floor(cell / width)
    const column = cell % width
    let sum      = 0
    for (let pixel = 0; pixel < cells; pixel++) {
      const x = column * across + (pixel % across)
      const y = row * down + Math.floor(pixel / across)
      sum += grayOf(screen, (y * SCREEN.width + x) * 4, observing.levels)
    }
    frame[cell] = Math.floor((sum + Math.floor(cells / 2)) / cells)
  }
}

/**
 * Counts the presses the episode `playing` sets out takes to end.
 */
export function stepsOf(playing: Partial<Playing> = PLAYING): number {
  const player = new Player(playing)
  player.finish()
  return player.episode.steps
}

/**
 * What the network reads at each step of one episode in place of Blue's
 * coordinates, `look` reading the pixels of the screen a step ends on, four
 * bytes a pixel, which `frames` holds turned to PyBoy's grays and shrunk for
 * each of the last steps, beside the squares reached the `grid` marks around
 * Blue and the event flags `flagged` reads. Every buffer is made once.
 */
export class Observation {
  readonly frames : readonly Uint8Array[]
  readonly grid   : Uint8Array
  readonly player : Player

  readonly #look      : () => ArrayLike<number>
  readonly #observing : Observing
  #newest             = 0

  constructor(
    look      : () => ArrayLike<number>,
    observing : Observing        = OBSERVING,
    playing   : Partial<Playing> = PLAYING
  ) {
    const { frame, grid, stack } = observing
    const area                   = frame.height * frame.width
    this.frames                  = Array.from({ length: stack }, () => new Uint8Array(area))
    this.grid                    = new Uint8Array(grid * grid)
    this.player                  = new Player(playing)
    this.#look                   = look
    this.#observing              = observing
  }

  /**
   * Reads whether each event flag is set, in the order `eventFlags` lists them.
   */
  get flagged(): boolean[] {
    return eventFlags.map(each => this.player.episode.flags.has(each.flag))
  }

  /**
   * Shrinks the screen the step ends on into the oldest frame, which becomes
   * the newest.
   */
  #capture(): void {
    this.#newest = (this.#newest + 1) % this.frames.length
    shrink(this.#look(), this.frames[this.#newest]!, this.#observing)
  }

  /**
   * Marks each square Blue has reached on the map he stands on, 1 where he has
   * reached it and 0 elsewhere, his own square at the grid's center and every
   * square farther from it than half the grid's side left off.
   */
  #mark(): void {
    const { at, place, reached } = this.player.episode
    const { grid: size }         = this.#observing
    const center                 = Math.floor(size / 2)
    this.grid.fill(0)
    for (let y = 0; y < WORLD[place].h; y++) {
      for (let x = 0; x < WORLD[place].w; x++) {
        const row    = y - at[1] + center
        const column = x - at[0] + center
        const inside = row >= 0 && row < size && column >= 0 && column < size
        if (inside && reached.has(squareKey(place, [x, y]))) this.grid[row * size + column] = 1
      }
    }
  }

  /**
   * Reads the frame `back` steps before the newest, the newest at 0.
   */
  frame(back: number): Uint8Array {
    return this.frames.at(this.#newest - back)!
  }

  /**
   * Presses once and reads what the network sees after the press.
   */
  next(): void {
    this.player.next()
    this.#capture()
    this.#mark()
  }

  /**
   * Plays the episode again from its start to `step`, capturing the screen of
   * each of the last steps on the way, and repeating the first step's screen
   * where fewer steps have passed, as Gymnasium's `FrameStackObservation`
   * repeats the screen a reset ends on.
   */
  seek(step: number): void {
    this.player.reset()
    for (let back = this.frames.length - 1; back >= 0; back--) {
      this.player.playTo(step - back)
      this.#capture()
    }
    this.#mark()
  }
}
