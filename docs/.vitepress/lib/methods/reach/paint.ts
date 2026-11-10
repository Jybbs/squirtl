import { clamp } from '@vueuse/core'

import WORLD                                        from '../../art/world.json' with { type: 'json' }
import { emoteRuns }                                from '../../front/learning/walker.ts'
import { frameFor }                                 from '../../game/actors.ts'
import type { Faded }                               from '../../game/fades.ts'
import { PLAIN, colorOf, paintGround, spriteFills } from '../../game/palettes.ts'
import type { Direction }                           from '../../game/rooms.ts'
import { LIFT, SQUARE, paintRuns, paintSprite }     from '../../game/screen.ts'
import { hueHex, roleHue }                          from '../../identity/identity.ts'
import * as reach                                   from '../reach.ts'

/**
 * The part of Pallet Town a screen shows, in squares: three columns round the
 * walk's, from half a square above the north edge's trees to half a square
 * into Oak's lab, the Game Boy's 144 lines, drawn at four times the game's
 * pixels so a pad's fill can stop between them.
 */
export const CROP = { h: 9, scale: 4, w: 3, x: 9, y: -0.5 } as const

/**
 * The fade palettes `home/fade.asm` steps through, written as `rBGP` is:
 * `FadePal5`, the screen as it stands, then `FadePal6`, `FadePal7`, and
 * `FadePal8`.
 */
export const PALETTES = [PLAIN, '2100', '1000', '0000'] as const

/**
 * Each arm of the pad as its left, top, width, and height in a square's pixels
 * and the way it fills outward from the pad's middle.
 */
const ARMS: Readonly<Record<Direction, readonly [number, number, number, number, number, number]>> = {
  down  : [6, 10, 4, 4, 0, 1],
  left  : [2, 6, 4, 4, -1, 0],
  right : [10, 6, 4, 4, 1, 0],
  up    : [6, 2, 4, 4, 0, -1]
}

/**
 * The agent's Denim every pad fills in.
 */
const AGENT = hueHex(roleHue('agent'))

/**
 * Reads where pressed square `k` sits on a screen, in the game's pixels.
 */
const squareOf = (k: number): [number, number] => [(reach.WALK[k]![0] - CROP.x) * SQUARE, (reach.WALK[k]![1] - CROP.y) * SQUARE]

/**
 * Draws the pad at pressed square `k`, its edge in the room's darkest shade
 * as the fade gives it, and each arm filled outward from the pad's middle as
 * far as `arms` reach, the fill fainter as the screen fades.
 */
function paintPad(context: CanvasRenderingContext2D, faded: Faded, k: number, arms: Record<Direction, number>, fade: number): void {
  const [x, y]      = squareOf(k)
  context.fillStyle = colorOf(faded.shades[Number(PALETTES[fade]![0])]!)
  context.fillRect(x + 5, y + 1, 6, 14)
  context.fillRect(x + 1, y + 5, 14, 6)
  context.fillStyle = colorOf(faded.shades[0]!)
  context.fillRect(x + 6, y + 2, 4, 12)
  context.fillRect(x + 2, y + 6, 12, 4)
  context.globalAlpha = 1 - fade / 3
  context.fillStyle   = AGENT
  for (const [press, [left, top, width, height, dx, dy]] of Object.entries(ARMS) as [Direction, (typeof ARMS)[Direction]][]) {
    const level = clamp(arms[press], 0, 1)
    if (level <= 0) continue
    const long = (dx ? width : height) * level
    context.fillRect(x + (dx < 0 ? left + width - long : left), y + (dy < 0 ? top + height - long : top), dx ? long : width, dy ? long : height)
  }
  context.globalAlpha = 1
}

/**
 * Draws Blue as `moment` shows him: mid-walk on his frame's stance, on his
 * first square facing Up before training, or at the north edge facing Down as
 * `PalletTownDefaultScript` turns him, his lower half behind the exit's tall
 * grass, as `UpdatePlayerSprite`'s grass priority draws it, and the shock
 * bubble over him while it shows.
 */
function paintBlue(context: CanvasRenderingContext2D, faded: Faded, moment: reach.Moment): void {
  const stride = reach.STRIDE[moment.walk]
  const edge   = !stride && moment.where === 'end'
  const square = reach.WALK[edge ? reach.PRESSES : 0]!
  const fills  = spriteFills(PALETTES[moment.fade]!)
  const x      = (square[0] - CROP.x) * SQUARE
  const y      = (stride ? stride.y : square[1] * SQUARE) - CROP.y * SQUARE - LIFT
  const pad    = WORLD.pallet.pad
  paintSprite(context, frameFor('player', edge ? 'down' : 'up', stride?.stance), x, y, fills)
  if (edge) context.drawImage(faded.over[moment.fade]!, (pad + square[0]) * SQUARE, (pad + square[1]) * SQUARE + LIFT, SQUARE, SQUARE / 2, x, y + SQUARE / 2, SQUARE, SQUARE / 2)
  if (moment.bubble && !stride) paintRuns(context, emoteRuns.shock, x, y - SQUARE, fills)
}

/**
 * Draws one screen of the walk onto `context` at `moment`, Pallet Town in the
 * fade's palette from `faded`, the pad on every square filled from `series` as
 * training stands `shared` of the way through landing, and Blue over them, or
 * the ground alone until the town's image loads.
 */
export function paintScreen(
  context : CanvasRenderingContext2D,
  faded   : Faded | null,
  series  : { odds: boolean, values: reach.Run[keyof Omit<reach.Run, 'copied'>] },
  shared  : number,
  moment  : reach.Moment
): void {
  const { h, scale, w, x, y } = CROP
  context.setTransform(scale, 0, 0, scale, 0, 0)
  context.imageSmoothingEnabled = false
  if (!faded) {
    paintGround(context, w * SQUARE, h * SQUARE)
    return
  }
  const pad = WORLD.pallet.pad
  context.drawImage(faded.map[moment.fade]!, (pad + x) * SQUARE, (pad + y) * SQUARE, w * SQUARE, h * SQUARE, 0, 0, w * SQUARE, h * SQUARE)
  for (let k = 0; k < reach.PRESSES; k++) {
    paintPad(context, faded, k, reach.armsOf(reach.valueAt(series.values, shared, k), k, series.odds), moment.fade)
  }
  paintBlue(context, faded, moment)
}
