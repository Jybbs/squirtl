import { PEOPLE }                               from '../../game/actors.ts'
import { squareKey }                            from '../../game/episode.ts'
import { Gait, type Placed, STEP, type Stance } from '../../game/gait.ts'
import * as rooms                               from '../../game/rooms.ts'
import { FIRST, LAST, MAPS, type Row, TRACE }   from '../memory.ts'

/**
 * Where Oak stands on a frame while he leads Blue, in squares, the way he
 * faces, and his stance.
 */
interface Oak {
  at     : readonly [x: number, y: number]
  facing : rooms.Direction
  stance : Stance
}

/**
 * One frame the episode shows: the room drawn and the fade over it, Blue's
 * place in squares and his facing and stance, Oak's while he leads, the Poké
 * Ball chosen, the square and the map the bytes hold, the row of the trace the
 * flags and the reached squares come from, and the frame's count on the one
 * clock every frame keeps.
 */
export interface Frame {
  at     : readonly [x: number, y: number]
  chosen : rooms.Square | null
  clock  : number
  facing : rooms.Direction
  fade   : number
  leader : Oak | null
  map    : number
  place  : rooms.Place
  row    : number
  square : rooms.Square
  stance : Stance
}

/**
 * Every frame the episode shows, a list a step, beside the frame each step
 * ends on.
 */
export interface Play {
  ends  : readonly Frame[]
  steps : readonly (readonly Frame[])[]
}

/**
 * `GBFadeOutToBlack`'s four background palettes, `FadePal4` to `FadePal1` in
 * pret/pokered's `home/fade.asm`, written as `rBGP` is, each held eight frames
 * as a warp darkens the room before the next one loads.
 */
export const FADE = ['3210', '3321', '3332', '3333'] as const

const FADE_FRAMES = 8

/**
 * The milliseconds one frame of the episode plays for, a step of the
 * environment's frames taking 180.
 */
export const FRAME_MS = 180 / STEP.frames

/**
 * The frames after a warp before the pad is read again, pret/pokered's
 * `IgnoreInputForHalfSecond`.
 */
const SETTLE = 30

/**
 * The passes of `OverworldLoop` a walk of one square takes, two pixels each.
 */
const PASSES = 8

/**
 * The doors of Pallet Town pret/pokered's `data/maps/objects/PalletTown.asm`
 * places into Blue's house and into Oak's lab, the second blocked in the model
 * until Oak leads Blue through it.
 */
const HOUSE_DOOR = rooms.RULES.pallet.warps[0].at

const LAB_DOOR: rooms.Square = [12, 11]

/**
 * Where Oak stands after a step while he leads Blue, standing in the lab's
 * door once Blue reaches the square below it.
 */
function oakAfter(row: Row): Placed | null {
  if (row.leader?.place === row.place) return row.leader
  if (row.place === 'pallet' && row.flags.has('appeared') && rooms.same(row.at, rooms.OAK_LEADS.at(-1)!)) return { at: LAB_DOOR, facing: 'up' }
  return null
}

/**
 * Reads the square a step from `was` to `row` walks Blue onto: his new square
 * on one room, the house's mat he stands on as he leaves it, the lab's door,
 * or the warp into the next room.
 */
function targetOf(was: Row, row: Row): rooms.Square {
  if (row.place === was.place) return row.at
  if (was.place === 'house') return was.at
  if (was.place === 'pallet' && row.place === 'lab') return LAB_DOOR
  return rooms.RULES[was.place].warps.find(warp => warp.to === row.place)!.at
}

/**
 * Plays the frames of one step through `gait`, from `was` to `row`.
 */
class StepFrames {
  readonly frames: Frame[] = []

  readonly #first : number
  readonly #gait  : Gait
  readonly #n     : number
  readonly #row   : Row
  readonly #was   : Row

  constructor(gait: Gait, n: number, first: number) {
    this.#first = first
    this.#gait  = gait
    this.#n     = n
    this.#row  = TRACE[n]!
    this.#was  = TRACE[n - 1]!
  }

  /**
   * Records a frame on `place` with Blue at `at`, standing in his gait's stance
   * unless given another, counted on the clock from the step's first frame.
   */
  record(place: rooms.Place, at: readonly [number, number], extra: Partial<Omit<Frame, 'clock'>> = {}): Frame {
    const was   = this.#was
    const frame = {
      at, chosen: was.chosen, clock: this.#first + this.frames.length, facing: this.#gait.facing, fade: 0, leader: null, map: MAPS[place], place,
      row: this.#n - 1, square: was.at, stance: this.#gait.stance, ...extra
    }
    this.frames.push(frame)
    return frame
  }

  /**
   * Runs the step's walk frame by frame as `Gait.frames` reads the pad, the
   * bytes taking the new square on the walk's last advance, and stops a walk
   * into a warp after the frame the warp starts on, once the pad has been read
   * on that frame.
   */
  walk(): void {
    const was     = this.#was
    const row     = this.#row
    const warped  = row.place !== was.place
    const exits   = warped && was.place === 'house'
    const target  = targetOf(was, row)
    const walks   = !rooms.same(target, was.at)
    const press   = rooms.DIRECTIONS.find(each => each === row.press) ?? null
    const dir     = exits ? 'down' : walks ? rooms.heading(was.at, target) : press
    const held    = row.scripted ? dir : row.press
    const oakFrom = warped ? null : oakAfter(was)
    const oakTo   = warped ? null : oakAfter(row) ?? (oakFrom && was.place === 'lab' ? PEOPLE.oak : null)
    let cut       = false
    for (const { f, read } of this.#gait.frames(this.#n - 1, held, !walks, row.turned)) {
      if (cut) break
      const t       = walks && f > read ? Math.min(PASSES, Math.ceil((f - read) / 2)) / PASSES : 0
      const settled = !warped && (walks ? t === 1 : f > read)
      const at      = walks ? [was.at[0] + rooms.MOVES[dir!][0] * t, was.at[1] + rooms.MOVES[dir!][1] * t] as const : was.at
      this.record(was.place, at, {
        ...(settled ? { chosen: row.chosen, row: this.#n, square: row.at } : {}),
        leader: oakBetween(oakFrom, oakTo, t, this.#gait.stance, settled)
      })
      cut = warped && (exits ? f === read : f === read + 2 * (PASSES - 1))
    }
    if (warped) this.#warp(target, exits)
  }

  /**
   * Fades the room out with `wCurMap` already holding the next room's number,
   * loads the next room, walks Blue down off Pallet Town's door where he left
   * the house, as `PlayerStepOutFromDoor` does, and holds the room until the
   * pad is read again.
   */
  #warp(target: rooms.Square, exits: boolean): void {
    const row  = this.#row
    const last = this.frames.at(-1)!
    for (let k = 0; k < FADE.length * FADE_FRAMES; k++) {
      this.record(last.place, target, { fade: Math.floor(k / FADE_FRAMES), map: MAPS[row.place], square: target })
    }
    const start = this.frames.length
    if (exits) {
      this.#gait.facing = 'down'
      this.record(row.place, HOUSE_DOOR, { square: HOUSE_DOOR, stance: 'standing' })
      for (let f = 1; f <= 2 * PASSES; f++) {
        if (f % 2 === 1) this.#gait.pass('down')
        const t       = Math.ceil(f / 2) / PASSES
        const arrived = t === 1
        this.record(row.place, [HOUSE_DOOR[0], HOUSE_DOOR[1] + t], arrived ? { row: this.#n, square: row.at } : { square: HOUSE_DOOR })
      }
    }
    const oak    = oakAfter(row)
    const leader = oak && { at: oak.at, facing: oak.facing, stance: 'standing' as const }
    while (this.frames.length - start < SETTLE) this.record(row.place, row.at, { chosen: row.chosen, leader, row: this.#n, square: row.at })
  }
}

/**
 * Reads where Oak stands `t` of the way between where he stood and where he
 * stands next, walking in `stance` where he moves, or where he stands alone
 * once the step settles.
 */
function oakBetween(from: Placed | null, to: Placed | null, t: number, stance: Stance, settled: boolean): Oak | null {
  if (from && to) {
    const moves = !rooms.same(from.at, to.at)
    return {
      at     : [from.at[0] + (to.at[0] - from.at[0]) * t, from.at[1] + (to.at[1] - from.at[1]) * t],
      facing : moves ? rooms.heading(from.at, to.at) : to.facing,
      stance : moves ? stance : 'standing'
    }
  }
  const only = settled ? to : from
  return only && { at: only.at, facing: only.facing, stance: 'standing' }
}

/**
 * Plays every step of the trace frame by frame as pret/pokered moves and draws
 * Blue, counting every frame on one clock from the first step's first frame,
 * and fades the last frame out before the bedroom loads again.
 */
function playOf(): Play {
  const gait  = new Gait(TRACE[0]!.facing)
  const first = TRACE[0]!
  const start = { at: first.at, chosen: null, clock: 0, facing: first.facing, fade: 0, leader: null, map: MAPS[first.place], place: first.place, row: 0, square: first.at, stance: 'standing' } as const
  let clock   = 0
  const steps: Frame[][] = [[]]
  for (let n = 1; n <= LAST; n++) {
    const step = new StepFrames(gait, n, clock)
    step.walk()
    steps.push(step.frames)
    clock += step.frames.length
  }
  const ends = [start, ...steps.slice(1).map(frames => frames.at(-1)!)]
  const last = ends[LAST]!
  steps[0] = [...FADE.flatMap((_, fade) => Array.from({ length: FADE_FRAMES }, () => ({ ...last, fade }))), ...Array.from({ length: SETTLE }, () => start)]
  return { ends, steps }
}

export const PLAY = playOf()

/**
 * The count of the frame each square is first shown on, so its mark settles
 * over a fixed count of frames from it whether the episode plays or holds.
 */
const SEEN: ReadonlyMap<string, number> = (() => {
  const seen = new Map([[squareKey(TRACE[0]!.place, TRACE[0]!.at), 0]])
  let shown  = 0
  for (const frame of PLAY.steps.slice(1).flat()) {
    for (; shown < frame.row; shown++) {
      const row = TRACE[shown + 1]!
      const key = squareKey(row.place, row.at)
      if (FIRST.get(key) === shown + 1) seen.set(key, frame.clock)
    }
  }
  return seen
})()

/**
 * A square the episode reaches, the step first standing on it, and the count
 * of the frame it is first shown on.
 */
export interface Reached {
  at   : rooms.Square
  seen : number
  step : number
}

/**
 * Every square the episode reaches in each room.
 */
export const REACHED: Readonly<Record<rooms.Place, readonly Reached[]>> = Object.groupBy(
  TRACE.flatMap((row, n) => FIRST.get(squareKey(row.place, row.at)) === n ? [{ at: row.at, place: row.place, seen: SEEN.get(squareKey(row.place, row.at))!, step: n }] : []),
  each => each.place
) as Record<rooms.Place, Reached[]>
