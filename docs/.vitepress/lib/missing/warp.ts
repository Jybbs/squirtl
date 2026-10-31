import type { Direction } from '../game/rooms.ts'

/**
 * Where a warp stands, the way Blue faces and his screen Y, the frames it has
 * written, the place in `SPIN` the next spin reads, the background palette the
 * screen shows, and the facing and the height the warp restores him to.
 */
interface Spinning extends WarpFrame {
  frames : WarpFrame[]
  next   : number
  saved  : Pick<WarpFrame, 'facing' | 'y'>
}

/**
 * Which parts of a warp play, Blue leaving the map and arriving back on it, and
 * the frames he stands still before he leaves and the screen holds white
 * between the two.
 */
export interface Warp {
  arrive? : boolean
  out?    : boolean
  stand?  : number
  white?  : number
}

/**
 * One of the Game Boy's frames of a warp, the way Blue faces, the background
 * palette the screen shows, and Blue's screen Y.
 */
export interface WarpFrame {
  facing  : Direction
  palette : string
  y       : number
}

/**
 * The background palettes pret/pokered's `home/fade.asm` steps through toward
 * white, written as `rBGP` lists the shades of colors 3 to 0: `FadePal5`, the
 * map as it stands, then `FadePal6`, `FadePal7`, and `FadePal8` (lines 70 to
 * 73), which `GBFadeOutToWhite` shows in turn and `GBFadeInFromWhite` walks
 * back from `FadePal7` (lines 26 to 63).
 */
export const FADE = ['3210', '2100', '1000', '0000'] as const

/**
 * The frames `GBFadeIncCommon` and `GBFadeDecCommon` hold each palette of a
 * fade, `ld c, 8` in `home/fade.asm` lines 37 and 59.
 */
const FADE_FRAMES = 8

/**
 * The frames `_LeaveMapAnim` waits once Blue has spun up off the screen from a
 * square that holds no warp pad, `ld c, 10` in
 * `engine/overworld/player_animations.asm` line 117.
 */
const PAD_WAIT = 10

/**
 * The facings Blue spins through in the order `PlayerSpinningFacingOrder`
 * lists them in `engine/overworld/player_animations.asm` lines 279 to 282,
 * which `SpinPlayerSprite` steps through one spin at a time from the facing he
 * holds.
 */
const SPIN: readonly Direction[] = ['down', 'left', 'up', 'right']

/**
 * The pixels each spin up or down moves Blue, `ld a, -$10` and `ld a, $10` in
 * `engine/overworld/player_animations.asm` lines 105 and 85.
 */
const SPIN_STEP = 16

/**
 * The frames `PlayerSpinWhileMovingUpOrDown` waits between spins, the 3 that
 * `GetPlayerTeleportAnimFrameDelay` gives off the Super Game Boy in
 * `engine/overworld/player_animations.asm` lines 343 to 348.
 */
const SPIN_WAIT = 3

/**
 * Blue's screen Y as the warp animations write `wSpritePlayerStateData1YPixels`:
 * `$3C` where he stands, the 4px lift above his square included, as
 * `ResetPlayerSpriteData` sets it in `home/reset_player_sprite.asm` line 10,
 * and `$EC`, past the screen's top, where a spin up stops and a spin down
 * starts, in `engine/overworld/player_animations.asm` lines 3 and 107.
 */
export const Y = { gone: 0xec - 256, stand: 0x3c }

/**
 * The warp the page at a missing address plays on a loop, Blue standing 150
 * frames, leaving as Teleport takes him, the screen holding white 30 frames,
 * and Blue arriving back on the same square.
 */
export const warpLoop = warpFrames({ stand: 150, white: 30 })

/**
 * Plays `EnterMapAnim` in `engine/overworld/player_animations.asm` lines 1 to
 * 40 from the white screen a warp leaves: Blue off the screen's top through
 * `Delay3`, `GBFadeInFromWhite`, five spins carrying him down onto his square
 * through `PlayerSpinWhileMovingDown` (lines 83 to 91), and a spin in place
 * slowing from 1 frame between spins to 7, before
 * `RestoreFacingDirectionAndYScreenPos` turns him back the way he faced.
 */
function enterMap(state: Spinning): void {
  initFacings(state)
  state.y       = Y.gone
  state.palette = FADE.at(-1)!
  hold(state, 3)
  for (const palette of FADE.slice(0, -1).toReversed()) {
    state.palette = palette
    hold(state, FADE_FRAMES)
  }
  spinMoving(state, SPIN_STEP, Y.stand)
  spinInPlace(state, 0, 1, 8)
  restore(state)
  hold(state, 1)
}

/**
 * Writes `count` frames of Blue as `state` stands him.
 */
function hold(state: Spinning, count: number): void {
  const { facing, palette, y } = state
  for (let n = 0; n < count; n++) state.frames.push({ facing, palette, y })
}

/**
 * Saves the way Blue faces and his height and sets the next spin to show his
 * own facing, as `InitFacingDirectionList` does in
 * `engine/overworld/player_animations.asm` lines 260 to 277.
 */
function initFacings(state: Spinning): void {
  state.saved = { facing: state.facing, y: state.y }
  state.next  = SPIN.indexOf(state.facing)
}

/**
 * Plays `_LeaveMapAnim` in `engine/overworld/player_animations.asm` lines 93
 * to 139 for Teleport, Dig, or an Escape Rope: a spin in place slowing from 15
 * frames between spins to 1, five spins carrying Blue up off the screen, the
 * wait off a warp pad, and `GBFadeOutToWhite`, before
 * `RestoreFacingDirectionAndYScreenPos` sets his facing and his height back
 * behind the white screen, which then holds `white` frames.
 */
function leaveMap(state: Spinning, white: number): void {
  initFacings(state)
  spinInPlace(state, 16, -1, 0)
  spinMoving(state, -SPIN_STEP, Y.gone)
  hold(state, PAD_WAIT)
  for (const palette of FADE.slice(1)) {
    state.palette = palette
    hold(state, FADE_FRAMES)
  }
  restore(state)
  hold(state, white)
}

/**
 * Turns Blue back to the facing and the height `initFacings` saved, as
 * `RestoreFacingDirectionAndYScreenPos` does in
 * `engine/overworld/player_animations.asm` lines 335 to 341.
 */
function restore(state: Spinning): void {
  state.facing = state.saved.facing
  state.y      = state.saved.y
}

/**
 * Shows the facing `SPIN` holds at the next spin's place and moves the place
 * on, as `SpinPlayerSprite` does in `engine/overworld/player_animations.asm`
 * lines 284 to 296.
 */
function spin(state: Spinning): void {
  state.facing = SPIN[state.next % SPIN.length]!
  state.next++
}

/**
 * Spins Blue in place as `PlayerSpinInPlace` does in
 * `engine/overworld/player_animations.asm` lines 298 to 317, each spin adding
 * `delta` to `wait` and holding the facing it shows that many frames, until a
 * spin brings `wait` to `end`.
 */
function spinInPlace(state: Spinning, wait: number, delta: number, end: number): void {
  spin(state)
  for (let next = wait + delta; next !== end; next += delta) {
    hold(state, next)
    spin(state)
  }
}

/**
 * Spins Blue up or down the screen as `PlayerSpinWhileMovingUpOrDown` does in
 * `engine/overworld/player_animations.asm` lines 319 to 333, each spin moving
 * him `step` pixels and holding the facing it shows for the frames between
 * spins, until a spin brings him to the screen Y `end`.
 */
function spinMoving(state: Spinning, step: number, end: number): void {
  spin(state)
  state.y += step
  while (state.y !== end) {
    hold(state, SPIN_WAIT)
    spin(state)
    state.y += step
  }
}

/**
 * Plays a warp frame by frame as pret/pokered's warp animations play it, Blue
 * starting on his square facing down and each spin showing the next facing of
 * `PlayerSpinningFacingOrder`.
 *
 * Returns:
 *   The frames of the warp, one to each of the Game Boy's frames.
 */
export function warpFrames(warp: Warp = {}): WarpFrame[] {
  const { arrive = true, out = true, stand = 0, white = 0 } = warp
  const state: Spinning = {
    facing  : 'down',
    frames  : [],
    next    : 0,
    palette : FADE[0],
    saved   : { facing: 'down', y: Y.stand },
    y       : Y.stand
  }
  hold(state, stand)
  if (out) leaveMap(state, white)
  if (arrive) enterMap(state)
  return state.frames
}
