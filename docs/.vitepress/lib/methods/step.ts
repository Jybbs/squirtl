import { Gait, STEP, type Stance } from '../game/gait.ts'
import { type Press, pressName }   from '../game/pad.ts'
import * as rooms                  from '../game/rooms.ts'
import { SQUARE }                  from '../game/screen.ts'

/**
 * One frame of a step as pret/pokered draws Blue in it, his facing, his
 * stance, and the pixels into his walk he stands, each frame showing the
 * passes of `OverworldLoop` before it.
 */
interface StepFrame {
  facing : rooms.Direction
  pixels : number
  stance : Stance
}

/**
 * One step of the sheet: its press, the square it starts on, the way it moves
 * Blue, none where it only turns him or walks nowhere, the frame the game reads
 * the pad on, and each of its frames.
 */
export interface SheetStep {
  frames : readonly StepFrame[]
  from   : rooms.Square
  move   : rooms.Square | null
  press  : Press
  read   : number
}

/**
 * Where the sheet's walk starts, Blue on his bedroom square having last stopped
 * facing left, and its ten presses round the floor and back, each change of
 * direction a step that only turns him, a press of A facing open floor and a
 * step with no press among them, so the loop starts again where it ends.
 */
export const START = { at: [3, 6] as rooms.Square, facing: 'left' as rooms.Direction }

const SCRIPT: readonly Press[] = ['right', 'right', 'up', 'up', 'a', 'down', 'down', null, 'left', 'left']

/**
 * The frames a step ticks and holds its press for.
 */
export const { frames: FRAMES, hold: HOLD } = STEP

/**
 * The pixels one pass of `OverworldLoop` moves a walk on, `AdvancePlayerSprite`
 * scrolling the map two pixels a pass.
 */
const PACE = 2

/**
 * The sheet's cells in pixels, one cell's side, the gap between two, and the
 * left and top of the part of the game screen a cell shows round Blue.
 */
export const SHEET = { cell: 24, crop: [60, 56], gap: 2 } as const

/**
 * The milliseconds the sheet rests on each frame, and on the frame PyBoy draws
 * at the end of a step.
 */
export const TEMPO = { rest: 700, tick: 90 } as const

/**
 * Runs `script` from `start` frame by frame through Blue's gait, a direction
 * other than the one he last stopped in only turning him and the game reading
 * the pad on frame 1 or frame 2 as the step is even or odd, since a step ticks
 * an odd count of frames.
 */
export function stepsOf(script: readonly Press[] = SCRIPT, start = START): SheetStep[] {
  const gait   = new Gait(start.facing)
  let at       = start.at
  let lastStop = start.facing
  return script.map((press, n) => {
    const direction = rooms.DIRECTIONS.find(each => each === press)
    const turn      = direction !== undefined && direction !== lastStop
    const move      = direction && !turn ? rooms.MOVES[direction] : null
    const frames    = Array.from(gait.frames(n, press, !move, turn), ({ f, read }): StepFrame => ({
      facing : gait.facing,
      pixels : move && f > read ? Math.min(SQUARE, PACE * Math.ceil((f - read) / 2)) : 0,
      stance : gait.stance
    }))
    const step = { frames, from: at, move, press, read: 1 + (n % 2) }
    if (direction) lastStop = direction
    if (move) at = rooms.neighbor(at, direction!)
    return step
  })
}

export const STEPS = stepsOf()

/**
 * Reads the square the view centers on during frame `f` of `step`, Blue's
 * square plus his pixels into his walk.
 */
export function viewAt(step: SheetStep, f: number): [number, number] {
  const { pixels } = step.frames[f - 1]!
  const [dx, dy]   = step.move ?? [0, 0]
  return [step.from[0] + dx * pixels / SQUARE, step.from[1] + dy * pixels / SQUARE]
}

/**
 * The sheet's position `at`, counted along its rows, as the step and the frame
 * from 1.
 */
export const cellOf = (at: number) => ({ f: at % FRAMES + 1, s: Math.floor(at / FRAMES) })

/**
 * Describes the position `at` for a screen reader.
 */
export function describe(at: number, steps: readonly SheetStep[] = STEPS): string {
  const { f, s } = cellOf(at)
  return `Step ${s + 1}, ${pressName(steps[s]!.press)}, frame ${f} of ${FRAMES}`
}

/**
 * The strength each frame shows at once the sheet stands at `at`: a frame the
 * position has passed half strength, the frame PyBoy draws and the one the
 * position stands on whole, and a frame still ahead faint.
 */
export function strengthOf(at: number, cell: number): number {
  if (cell > at) return 0.14
  return cell === at || cell % FRAMES === FRAMES - 1 ? 1 : 0.5
}
