import { clamp } from '@vueuse/core'

import type { Stance } from '../game/gait.ts'
import * as rooms      from '../game/rooms.ts'
import { SQUARE }      from '../game/screen.ts'
import SETTINGS        from '../rendered/settings.json' with { type: 'json' }
import { stepsOf }     from './step.ts'

/**
 * What one learner holds at every pressed square of the walk after each pass,
 * pass 0 before training: the deep Q-network's online network and its copy,
 * whether a pass took the copy, PQN's one network, and PPO's odds of pressing
 * Up and its critic's guess.
 */
export interface Run {
  copied : readonly boolean[]
  copy   : readonly (readonly number[])[]
  critic : readonly (readonly number[])[]
  odds   : readonly (readonly number[])[]
  online : readonly (readonly number[])[]
  pqn    : readonly (readonly number[])[]
}

/**
 * What one frame of the loop shows: the fade palette, the pass playing, the
 * pass whose values have landed, the frame of Blue's walk or none, where he
 * stands once he is not walking, and whether the shock bubble shows.
 */
export interface Moment {
  bubble : boolean
  fade   : number
  landed : number
  pass   : number
  walk   : number
  where  : 'end' | 'start'
}

/**
 * One frame of Blue's walk up the column, his stance and the pixel row of the
 * top of his square.
 */
export interface Stride {
  stance : Stance
  y      : number
}

/**
 * The discount every learner reads from the settings, PQN's λ, and PPO's clip
 * ε and advantage λ, each as its learner's settings declare it.
 */
const LEARNING = {
  discount : SETTINGS.agent.discount,
  epsilon  : SETTINGS.agent.ppo.clip_range,
  gae      : SETTINGS.agent.ppo.trace_decay,
  lambda   : SETTINGS.agent.pqn.trace_decay
} as const

/**
 * Blue's squares from 10, 7 up Pallet Town's tenth column to the north edge at
 * 10, 1, where pret/pokered's `PalletTownDefaultScript` sets
 * `EVENT_OAK_APPEARED_IN_PALLET` and the reward pays its milestone.
 */
export const WALK: readonly rooms.Square[] = [[10, 7], [10, 6], [10, 5], [10, 4], [10, 3], [10, 2], [10, 1]]

export const PRESSES = WALK.length - 1

/**
 * The passes the loop plays, and the passes the deep Q-network takes its copy
 * at the start of, every second one.
 */
export const PASSES = 8

const COPY_EVERY = 2

/**
 * The value before training of the press every network rates best at each
 * pressed square, falling toward the north edge so nothing a network reads from
 * it outranks it, and that press, Left or Right, beside PPO's critic's share of
 * its gap a pass and the scale on its advantage before the clip.
 */
export const NOISE: readonly number[] = [0.010, 0.009, 0.008, 0.007, 0.006, 0.005]

const FAVORED: readonly rooms.Direction[] = ['right', 'left', 'right', 'left', 'left', 'right']

const PPO = { critic: 0.35, scale: 3 } as const

/**
 * The presses a learner chooses among, each of the Game Boy's buttons and no
 * press at all.
 */
export const ACTIONS = rooms.BUTTONS.length + 1

/**
 * Clips PPO's ratio of new odds to old to 1 ± ε.
 */
const clip = (ratio: number): number => clamp(ratio, 1 - LEARNING.epsilon, 1 + LEARNING.epsilon)

/**
 * Trains every learner over the walk pass by pass, the walk paying 1 where Oak
 * calls Blue back and nothing before, each update moving a value all the way
 * to its target. The deep Q-network aims at the payment plus the discount times
 * its copy's value, at the next square, of the press its online network rates
 * best there. PQN aims each press at its λ-return, run back from the walk's end
 * over its own values. PPO raises its odds of Up by the generalized advantage
 * of the walk over its critic's guess, the ratio of new odds to old clipped to
 * 1 ± ε, and its critic covers its share of the gap.
 */
function runOf(): Run {
  const n     = PRESSES
  const paid  = (k: number) => k === n - 1 ? 1 : 0
  const fill  = (value: number) => Array.from({ length: n }, () => value)
  const run   = { copied: [false], copy: [fill(0)], critic: [fill(0)], odds: [fill(1 / ACTIONS)], online: [fill(0)], pqn: [fill(0)] }
  for (let p = 1; p <= PASSES; p++) {
    const copied                  = (p - 1) % COPY_EVERY === 0
    const [online, pqn, critic]   = [run.online[p - 1]!, run.pqn[p - 1]!, run.critic[p - 1]!]
    const copy                    = copied ? online : run.copy[p - 1]!
    const read                    = (k: number) => k === n ? 0 : online[k]! > NOISE[k]! ? copy[k]! : NOISE[k]!
    const returns: number[]       = []
    const advantage: number[]     = []
    for (let k = n - 1; k >= 0; k--) {
      const ahead = k === n - 1 ? 0 : (1 - LEARNING.lambda) * Math.max(pqn[k + 1]!, NOISE[k + 1]!) + LEARNING.lambda * returns[k + 1]!
      returns[k]  = paid(k) + LEARNING.discount * ahead
    }
    for (let carry = 0, k = n - 1; k >= 0; k--) {
      carry        = paid(k) + LEARNING.discount * (critic[k + 1] ?? 0) - critic[k]! + LEARNING.discount * LEARNING.gae * carry
      advantage[k] = carry
    }
    run.copied.push(copied)
    run.copy.push(copy)
    run.online.push(online.map((_, k) => paid(k) + LEARNING.discount * read(k + 1)))
    run.pqn.push(returns)
    run.odds.push(run.odds[p - 1]!.map((odds, k) => Math.min(1, odds * clip(1 + PPO.scale * advantage[k]!))))
    run.critic.push(critic.map((guess, k) => guess + PPO.critic * advantage[k]!))
  }
  return run
}

export const RUN = runOf()

/**
 * Blue's walk up the column frame by frame as pret/pokered moves him, each
 * press's frames through his gait.
 */
export const STRIDE: readonly Stride[] = stepsOf(Array.from({ length: PRESSES }, () => 'up'), { at: WALK[0]!, facing: 'up' })
  .flatMap((step, n) => step.frames.map(frame => ({ stance: frame.stance, y: WALK[n]![1] * SQUARE - frame.pixels })))

/**
 * The loop's lengths in Game Boy frames: each fade palette's hold, as
 * `home/fade.asm`'s `DelayFrames 8` holds it, the frames the shock bubble
 * stays, as `EmotionBubble` holds it with `DelayFrames 60`, the frames a pass's
 * values take to settle, three of the identity's steps, the frames the copy
 * takes, and the holds before the first pass and after the last.
 */
export const FRAMES = { bubble: 60, copy: 9, fade: 8, settle: 27, end: 150, start: 60 } as const

/**
 * The loop's marks in frames: the start of the first pass, one pass, the end
 * of the last, and the whole loop with its fades.
 */
export const LINE = (() => {
  const pass  = STRIDE.length + FRAMES.bubble
  const start = 3 * FRAMES.fade + FRAMES.start
  const end   = start + PASSES * pass
  return { end, pass, start, total: end + FRAMES.end + 3 * FRAMES.fade }
})()

/**
 * Reads what frame `clock` of the loop shows: fading in from white through
 * `FadePal7` and `FadePal6` and out through `FadePal6` to `FadePal8`, the hold
 * before training, each pass's walk and then its values landing under the
 * shock bubble, and the hold after the last pass.
 */
export function momentAt(clock: number): Moment {
  const moment: Moment = { bubble: false, fade: 0, landed: 0, pass: 0, walk: -1, where: 'start' }
  if (clock < LINE.start) return { ...moment, fade: clock < 3 * FRAMES.fade ? 2 - Math.floor(clock / FRAMES.fade) : 0 }
  if (clock >= LINE.end) {
    const out = clock - LINE.end - FRAMES.end
    return { ...moment, fade: out >= 0 ? 1 + Math.floor(out / FRAMES.fade) : 0, landed: PASSES, pass: PASSES, where: 'end' }
  }
  const into  = clock - LINE.start
  const local = into % LINE.pass
  const pass  = 1 + Math.floor(into / LINE.pass)
  if (local < STRIDE.length) return { ...moment, landed: pass - 1, pass, walk: local }
  return { ...moment, bubble: true, landed: pass, pass, where: 'end' }
}

/**
 * Reads the frame of the loop that holds pass `pass` landed, Blue at the north
 * edge under the shock bubble, or before training, Blue on his first square.
 */
export const clockOf = (pass: number): number => pass ? LINE.start + (pass - 1) * LINE.pass + STRIDE.length : 3 * FRAMES.fade

/**
 * Reads the value `series` holds at pressed square `k` a share of the way
 * between two passes, `at` counting passes from before training.
 */
export function valueAt(series: readonly (readonly number[])[], at: number, k: number): number {
  const before = series[Math.floor(at)]![k]!
  return before + (series[Math.ceil(at)]![k]! - before) * (at - Math.floor(at))
}

/**
 * Reads how far each arm of the pad at pressed square `k` fills: for a
 * network, its value `up` of pressing Up and its value before training of the
 * press it favored there, and for PPO, its odds `up` of pressing Up and the
 * rest shared among every other press.
 */
export function armsOf(up: number, k: number, odds: boolean): Record<rooms.Direction, number> {
  if (odds) {
    const rest = (1 - up) / (ACTIONS - 1)
    return { down: rest, left: rest, right: rest, up }
  }
  return { down: 0, left: 0, right: 0, [FAVORED[k]!]: NOISE[k]!, up }
}

/**
 * Names pass `pass` for the slider and for a screen reader.
 */
export const passName = (pass: number): string => pass ? `After pass ${pass} of ${PASSES}` : 'Before training'
