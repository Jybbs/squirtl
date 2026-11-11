import { clamp } from '@vueuse/core'

import { actorsOf, frameFor }        from '../../game/actors.ts'
import { paintGround, spriteFills }  from '../../game/palettes.ts'
import * as rooms                    from '../../game/rooms.ts'
import { LIFT, SQUARE, paintSprite } from '../../game/screen.ts'
import { hueHex, roleHue }           from '../../identity/identity.ts'
import { NEWEST }                    from '../memory.ts'
import * as marks                    from './marks.ts'
import { FADE, type Frame, REACHED } from './play.ts'

/**
 * The novelty term's hue every square reached is marked in.
 */
const NOVELTY = hueHex(roleHue('novelty'))

/**
 * The entries of the key a drawing reads, as their places in it.
 */
const LIT = { newest: 1, reached: 0 } as const

/**
 * Reads how strongly a square's mark shows while the key's entry `lit` is
 * picked out: stronger for every square reached, full for the newest alone
 * while the newest is, and fainter for any other entry.
 */
export function strengthOf(lit: number | null, newest: boolean): number {
  if (lit === null || (lit === LIT.newest && newest)) return 1
  return lit === LIT.reached ? 1.5 : 0.4
}

/**
 * Draws `shape` with its square's top left at `x` and `y`.
 */
function paintShape(context: CanvasRenderingContext2D, shape: marks.Shape, x: number, y: number): void {
  for (const [dx, dy, width] of shape) context.fillRect(x + dx, y + dy, width, 1)
}

/**
 * Marks every square the episode has reached by `frame`'s step with a dot that
 * pops in large and settles small over the frames after it first shows, lighter
 * the more steps have passed since, and rings the newest.
 */
function paintSquares(context: CanvasRenderingContext2D, frame: Frame, lit: number | null): void {
  const fade   = 1 - frame.fade / 3
  const newest = NEWEST[frame.row]!.place === frame.place ? NEWEST[frame.row]!.at : null
  context.fillStyle = NOVELTY
  for (const square of REACHED[frame.place] ?? []) {
    if (square.step > frame.row) continue
    const own     = newest !== null && rooms.same(square.at, newest)
    const settled = clamp((frame.clock - square.seen) / marks.TIMING.settle, 0, 1)
    const age     = Math.min(1, (frame.row - square.step) / marks.TIMING.age)
    context.globalAlpha = Math.min(1, (0.95 - 0.5 * age) * strengthOf(lit, own)) * fade
    paintShape(context, marks.dotOf(settled, own), square.at[0] * SQUARE, square.at[1] * SQUARE)
  }
  if (newest) {
    context.globalAlpha = (lit !== null && lit > LIT.newest ? 0.4 : 1) * fade
    paintShape(context, marks.SHAPES.ring14, newest[0] * SQUARE, newest[1] * SQUARE)
  }
  context.globalAlpha = 1
}

/**
 * Draws everyone standing in the room and Blue over it in the fade's shades,
 * nobody once the room has faded to black.
 */
function paintPeople(context: CanvasRenderingContext2D, frame: Frame): void {
  if (frame.fade === FADE.length - 1) return
  const fills  = spriteFills(FADE[frame.fade]!)
  const leader = frame.leader && { at: frame.leader.at as rooms.Square, facing: frame.leader.facing, place: frame.place }
  const sprite = (pose: ReturnType<typeof frameFor>, at: readonly [number, number]) =>
    paintSprite(context, pose, Math.round(at[0] * SQUARE), Math.round(at[1] * SQUARE) - LIFT, fills)
  for (const actor of actorsOf({ chosen: frame.chosen, leader, place: frame.place }, leader?.at, frame.leader?.stance)) {
    sprite(frameFor(actor.name, actor.facing, actor.stance), actor.at)
  }
  sprite(frameFor('player', frame.facing, frame.stance), frame.at)
}

/**
 * Draws `frame` onto the map of its room: the room in the fade's palette from
 * `faded`, the renders of the room in each palette of the fade, the squares
 * reached as the key's entry `lit` picks them out, and the people, or the
 * ground alone until the room's image loads.
 */
export function paintMap(context: CanvasRenderingContext2D, faded: readonly CanvasImageSource[] | undefined, frame: Frame, lit: number | null): void {
  const { cols, rows }          = marks.fitOf(frame.place)
  context.imageSmoothingEnabled = false
  if (!faded) {
    paintGround(context, cols * SQUARE, rows * SQUARE)
    return
  }
  context.drawImage(faded[frame.fade]!, 0, 0)
  paintSquares(context, frame, lit)
  paintPeople(context, frame)
}
