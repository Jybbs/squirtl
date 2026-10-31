import SETTINGS from '../rendered/settings.json' with { type: 'json' }
import * as rooms from './rooms.ts'

/**
 * Blue's place after one press of a walk, as far as his gait reads it, the
 * square he stands on and the way he faces.
 */
export interface Placed {
  at     : rooms.Square
  facing : rooms.Direction
}

/**
 * A stance of the walk's animation, standing, walking, or walking on the other
 * foot, the walking frame mirrored.
 */
export type Stance = (typeof STANCES)[number]

/**
 * How one step runs, the frames the step ticks and the frames the emulator
 * holds its button for at the step's start.
 */
export interface Step {
  frames : number
  hold   : number
}

/**
 * The stance each of the walk animation's four frames shows, standing, walking,
 * standing, and walking through `.FlippedOAM`, as pret/pokered's
 * `SpriteFacingAndAnimationTable` lists them in `data/sprites/facings.asm`
 * lines 3 to 18 and `.FlippedOAM` mirrors them in lines 54 to 59.
 */
const ANIMATION: readonly Stance[] = ['standing', 'walking', 'standing', 'mirrored']

/**
 * The passes of `OverworldLoop` a walk of one square runs after the pass that
 * starts it, `wWalkCounter` starting at 8 in `home/overworld.asm` lines 263
 * and 264 and `AdvancePlayerSprite` moving Blue two pixels a pass.
 */
const PASSES = 7

/**
 * The stances a sprite shows, standing, walking, and walking mirrored.
 */
const STANCES = ['standing', 'walking', 'mirrored'] as const

/**
 * How every step runs, the frames `EnvironmentSettings.frames_per_step` ticks
 * and the frames `EmulatorSettings.hold` holds the button for.
 */
export const STEP: Step = { frames: SETTINGS.environment.frames_per_step, hold: SETTINGS.emulator.hold }

/**
 * The ticks of `UpdatePlayerSprite`'s animation counter between two frames of
 * the walk's animation, which `engine/overworld/movement.asm` lines 60 to 78
 * count.
 */
const TICKS = 4

/**
 * Blue's gait as pret/pokered moves and animates him, one pass of
 * `OverworldLoop` every second frame.
 *
 * A walk under way counts a tick of `UpdatePlayerSprite`'s animation each pass.
 * A direction held with no walk under way faces Blue to it, counts a tick, and
 * starts a walk unless the square ahead is blocked, whereas a direction other
 * than the one he last stopped in only sets the way he moves through
 * `.holdIntermediateDirectionLoop` in `home/overworld.asm`, with no tick. A
 * pass with no direction held after one was counts one more tick and clears the
 * direction, as `.noDirectionButtonsPressed` does in lines 132 to 145, and the
 * pass after that zeroes the counters, as `UpdatePlayerSprite`'s `.notMoving`
 * does in `engine/overworld/movement.asm` lines 49 to 54. Every fourth tick
 * moves the animation on a frame, so the counters carry across consecutive
 * steps and a walk down or up alternates the plain walking frame and the
 * mirrored one.
 */
export class Gait {
  facing: rooms.Direction

  #frame  = 0
  #moving : rooms.Direction | null = null
  #ticks  = 0
  #walk   = 0

  constructor(facing: rooms.Direction = 'down') {
    this.facing = facing
  }

  /**
   * Reads the stance the animation's current frame shows.
   */
  get stance(): Stance {
    return ANIMATION[this.#frame]!
  }

  /**
   * Counts one tick of the animation, moving it a frame on every fourth.
   */
  #tick(): void {
    this.#ticks = (this.#ticks + 1) % TICKS
    if (this.#ticks === 0) this.#frame = (this.#frame + 1) % ANIMATION.length
  }

  /**
   * Runs one pass of `OverworldLoop` with `held` pressed, a walk not starting
   * where `blocked` is set and a press turning Blue in place where `turn` is.
   */
  pass(held: rooms.Button | null, blocked = false, turn = false): void {
    if (this.#walk > 0) {
      this.#walk--
      this.#tick()
      return
    }
    if (held === 'a') return
    if (held && held !== 'b') {
      this.#moving = held
      if (turn) return
      this.facing = held
      this.#tick()
      if (!blocked) this.#walk = PASSES
      return
    }
    if (!this.#moving) {
      this.#frame = 0
      this.#ticks = 0
      return
    }
    this.facing  = this.#moving
    this.#moving = null
    this.#tick()
  }

  /**
   * Stands Blue still facing `facing`, his walk and his animation's counters
   * cleared, after a jump or a change of room.
   */
  reset(facing: rooms.Direction): void {
    this.facing  = facing
    this.#frame  = 0
    this.#moving = null
    this.#ticks  = 0
    this.#walk   = 0
  }

  /**
   * Runs the `n`th step of an episode frame by frame, `held` pressed for the
   * step's hold and the game reading the pad every second frame from its first
   * or its second as `n` is even or odd, since a step ticks an odd count of
   * frames, and writes the stance Blue shows on each frame into `stances`.
   *
   * Returns:
   *   The stances, one to each of the step's frames.
   */
  step(
    n       : number,
    held    : rooms.Button | null,
    blocked : boolean,
    turn    : boolean,
    stances : Stance[],
    step    : Step = STEP
  ): Stance[] {
    const read = 1 + (n % 2)
    for (let frame = 1; frame <= step.frames; frame++) {
      stances[frame - 1] = this.stance
      const reads = frame >= read && (frame - read) % 2 === 0
      if (reads) this.pass(frame <= step.hold ? held : null, blocked, turn)
    }
    return stances
  }
}

/**
 * Reads the stance of `stances`, one step's, Blue shows `t` of the way through
 * the step, the last frame's once it ends.
 */
export function stanceAt(stances: readonly Stance[], t: number): Stance {
  return stances[Math.min(stances.length - 1, Math.floor(t * stances.length))]!
}

/**
 * Runs Blue's gait through each press of a walk of `places`, his place before
 * the first press and after each one, a press that reaches no new square
 * blocked and one that faces him another way turning him.
 *
 * Returns:
 *   The stances of each press, one to each of its frames.
 */
export function stancesOf(places: readonly Placed[], step: Step = STEP): Stance[][] {
  const gait = new Gait(places[0]?.facing)
  return places.slice(1).map((to, press) => {
    const from    = places[press]!
    const walked  = !rooms.same(from.at, to.at)
    const turned  = !walked && to.facing !== from.facing
    const stances = Array.from({ length: step.frames }, (): Stance => 'standing')
    return gait.step(press, to.facing, !walked, turned, stances, step)
  })
}
