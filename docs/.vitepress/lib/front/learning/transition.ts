import WORLD                                 from '../../art/world.json' with { type: 'json' }
import { PLAIN, colorOf, recolor, shadesOf } from '../../game/palettes.ts'
import { FRAME, LIFT, type Painter, SQUARE } from '../../game/screen.ts'

/**
 * When each part of the transition into a wild battle starts and ends, in
 * milliseconds from its start, beside how long one flash palette, one step of
 * the double circle, and one palette of the fade hold.
 */
export interface Phases {
  black      : number
  circle     : number
  circleStep : number
  end        : number
  fadeStep   : number
  flash      : number
  flashStep  : number
}

/**
 * The canvas members the town's view is read through once its image loads.
 */
export type Reader = Pick<CanvasRenderingContext2D, 'createImageData' | 'drawImage' | 'getImageData'>

/**
 * One eight-pixel tile of the town's view and the step of the double circle
 * that blacks it.
 */
export interface Tile {
  column : number
  row    : number
  step   : number
}

/**
 * The town's view in each palette the transition shows, the darkest of its
 * shades, which the double circle closes in, and each of the view's tiles by
 * the step of the double circle that blacks it.
 */
export interface Town {
  ink      : string
  palettes : ReadonlyMap<string, ImageData>
  tiles    : readonly Tile[]
}

/**
 * The still view of the town the walks play on, its height and width in pixels,
 * the pixels a sprite stands above its square, and the square at its top left.
 */
export interface TownView {
  height : number
  lift   : number
  width  : number
  x      : number
  y      : number
}

/**
 * pret/pokered's timing of the transition into a wild battle, counted in the
 * Game Boy's frames of `frame` milliseconds: the frames each palette of
 * `BattleTransition_FlashScreen` holds and the runs it makes through them, the
 * steps of `BattleTransition_DoubleCircle` and the frames between them, the
 * frames the screen holds black, and the frames each palette of the fade back
 * in holds.
 */
export interface Transition {
  blackFrames  : number
  circleFrames : number
  circleSteps  : number
  fadeFrames   : number
  flashFrames  : number
  flashRuns    : number
  frame        : number
}

/**
 * The background palette with every color of the town set to the darkest shade,
 * written as the Game Boy's `rBGP` lists the shades of colors 3 to 0.
 */
const BLACK = '3333'

/**
 * The palettes the game fades back in through from black.
 */
const FADE_IN = ['3333', '3332', '3321', '3210'] as const

/**
 * The palettes of pret/pokered's `BattleTransition_FlashScreenPalettes`, in the
 * order the flash shows them.
 */
const FLASH = [
  '3321', '3332', '3333', '3332', '3321', '3210', '2100', '1000', '0000', '1000', '2100', '3210'
] as const

/**
 * The pixels on each side of one of the Game Boy's background tiles, the unit
 * the double circle blacks the screen in.
 */
const TILE = 8

/**
 * The transition's timing as pret/pokered runs it, in frames of the length the
 * Game Boy draws one. `BattleTransition_FlashScreen` holds each palette 2
 * frames over 3 runs and `BattleTransition_DoubleCircle` takes 10 steps 3
 * frames apart, both in `engine/battle/battle_transitions.asm`, which holds the
 * screen black 10 frames after `BattleTransition_BlackScreen` at the end of its
 * shrinking and splitting transitions, and `GBFadeInFromBlack` in
 * `home/fade.asm` holds each palette of the fade back in 8 frames.
 */
export const TRANSITION: Transition = {
  blackFrames  : 10,
  circleFrames : 3,
  circleSteps  : 10,
  fadeFrames   : 8,
  flashFrames  : 2,
  flashRuns    : 3,
  frame        : FRAME
}

/**
 * The town's north half, every square the walks reach from the west edge to the
 * east, from just above the north edge down past Blue's door.
 */
export const VIEW: TownView = { height: 152, lift: LIFT, width: 320, x: 0, y: -0.25 }

/**
 * When each part of the transition starts and ends, in milliseconds.
 */
export const battlePhases = phasesOf()

/**
 * Every background palette the transition shows, each named once.
 */
const townPalettes = [...new Set<string>([PLAIN, BLACK, ...FLASH, ...FADE_IN])]

/**
 * Orders every tile of `view` by the step of `steps` at which the double circle
 * blacks it, its top half sweeping clockwise from the left edge while its
 * bottom half sweeps from the right.
 */
export function circleTilesOf(steps: number = TRANSITION.circleSteps, view: TownView = VIEW): Tile[] {
  const columns = view.width / TILE
  const rows    = Math.ceil(view.height / TILE)
  return Array.from({ length: rows * columns }, (_, at) => {
    const column = at % columns
    const row    = Math.floor(at / columns)
    const angle  = Math.atan2(row + 0.5 - rows / 2, column + 0.5 - columns / 2)
    const swept  = (angle < 0 ? angle + Math.PI : angle) / Math.PI
    return { column, row, step: Math.min(steps - 1, Math.floor(swept * steps)) }
  })
}

/**
 * Fills in the darkest shade of `town` every tile of its view the double circle
 * has blacked by its step `step`.
 */
export function paintCircle(context: Painter, step: number, town: Pick<Town, 'ink' | 'tiles'>): void {
  context.fillStyle = town.ink
  for (const tile of town.tiles) {
    if (tile.step <= step) context.fillRect(tile.column * TILE, tile.row * TILE, TILE, TILE)
  }
}

/**
 * Reads the background palette the transition shows `t` milliseconds in: the
 * flash's palettes in turn, the town's own while the circle closes, black, and
 * then each palette of the fade back in.
 */
export function paletteAt(t: number, phases: Phases = battlePhases): string {
  if (t < phases.flash) return FLASH[Math.floor(t / phases.flashStep) % FLASH.length]!
  if (t < phases.circle) return PLAIN
  if (t < phases.black) return BLACK
  return FADE_IN[Math.min(FADE_IN.length - 1, Math.floor((t - phases.black) / phases.fadeStep))]!
}

/**
 * Reads when each part of the transition starts and ends from the frames
 * `transition` counts.
 */
export function phasesOf(transition: Transition = TRANSITION): Phases {
  const { blackFrames, circleFrames, circleSteps, fadeFrames, flashFrames, flashRuns, frame } = transition
  const flash  = flashRuns * FLASH.length * flashFrames * frame
  const circle = flash + circleSteps * circleFrames * frame
  const black  = circle + blackFrames * frame
  return {
    black      : black,
    circle     : circle,
    circleStep : circleFrames * frame,
    end        : black + FADE_IN.length * fadeFrames * frame,
    fadeStep   : fadeFrames * frame,
    flash      : flash,
    flashStep  : flashFrames * frame
  }
}

/**
 * Reports whether the sprites show `t` milliseconds into the transition, which
 * they do until the circle closes and again once the fade lifts black.
 */
export function spritesAt(t: number, phases: Phases = battlePhases): boolean {
  return t < phases.circle || paletteAt(t, phases) !== BLACK
}

/**
 * Reads the step of the double circle that has closed `t` milliseconds into the
 * transition, or -1 outside the circle's steps.
 */
export function tileStepAt(t: number, phases: Phases = battlePhases): number {
  return t >= phases.flash && t < phases.circle ? Math.floor((t - phases.flash) / phases.circleStep) : -1
}

/**
 * Draws the town's view of `view` from Pallet Town's image onto `context` and
 * reads it back in every palette the transition shows, made once and kept,
 * beside the view's tiles by the step of the double circle that blacks each.
 */
export function townFrom(context: Reader, image: CanvasImageSource, view: TownView = VIEW): Town {
  const { height, width, x, y } = view
  const { pad }                 = WORLD.pallet
  context.drawImage(image, (x + pad) * SQUARE, (y + pad) * SQUARE, width, height, 0, 0, width, height)
  const base     = context.getImageData(0, 0, width, height)
  const shades   = shadesOf(base.data)
  const palettes = new Map(townPalettes.map(palette => {
    const shaded = context.createImageData(width, height)
    recolor(palette, shades, base.data, shaded.data)
    return [palette, shaded] as const
  }))
  return { ink: colorOf(shades.at(-1)!), palettes, tiles: circleTilesOf(TRANSITION.circleSteps, view) }
}
