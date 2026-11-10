import { clamp } from '@vueuse/core'

import { type Press, pressName } from '../game/pad.ts'
import { Player }                from '../game/player.ts'
import { count }                 from '../widgets/numbers.ts'

/**
 * Where a check stands, waiting for its values, comparing them, or once they
 * match.
 */
export type Check = 'pass' | 'run' | 'wait'

/**
 * One step of the recording, its press and the return after it.
 */
export interface Recorded {
  press : Press
  total : number
}

/**
 * The run the widget plays back, a digest and a `timer_div` standing in for
 * the ones a run's `run.json` and `episodes.jsonl` record, beside the episode
 * the agent's stand-in plays in the model of the first rooms.
 */
export const RUN = {
  digest   : '204212f5b2f2bc0eb43d677b185ea393746d110c19a0ac982b0e68a497d452d7',
  timerDiv : 92
}

/**
 * Each step of the episode the widget plays back from the reset, the first
 * the reset itself with no press, played by the agent's stand-in.
 */
function recordingOf(player = new Player()): Recorded[] {
  return [{ press: null, total: 0 }, ...player.steps().map(() => ({ press: player.button, total: player.episode.total }))]
}

export const RECORDING = recordingOf()

/**
 * The last step of the recording, the count of its presses.
 */
export const LAST = RECORDING.length - 1

/**
 * The steps PyBoy's window plays a second, a step's frames to each of its
 * ticks.
 */
export const RATE = 60

/**
 * The phases of one playback, in milliseconds from the window opening: the
 * window fading in, the intro's digest compared, the reset fading in, the
 * last press played, and the hold before the window fades out and closes.
 */
export const PHASES = (() => {
  const open   = 400
  const digest = open + 1500
  const reset  = digest + 300
  const play   = reset + LAST / RATE * 1000
  const hold   = play + 3700
  return { close: hold + 400, digest, hold, open, play, reset }
})()

/**
 * The milliseconds before a phase's end its comparison settles, the digest's
 * digits matching and the return's check reporting a match.
 */
const SETTLE = 500

/**
 * Formats a return as `squirtl watch` logs it, to four places.
 */
export const returned = (value: number): string => value.toFixed(4)

/**
 * Reads the step the playback has reached at `t`, none before the reset.
 */
export const stepAt = (t: number): number =>
  t < PHASES.reset ? 0 : clamp(Math.floor((t - PHASES.reset) / 1000 * RATE), 0, LAST)

/**
 * Reads the time at which the playback stands halfway through step `step`.
 */
export const timeOf = (step: number): number => PHASES.reset + (step + 0.5) / RATE * 1000

/**
 * Reads where the intro's check stands at `t`.
 */
export function introAt(t: number): Check {
  if (t < PHASES.open) return 'wait'
  return t < PHASES.digest - 300 ? 'run' : 'pass'
}

/**
 * Reads where the return's check stands at `t`.
 */
export function endingAt(t: number): Check {
  if (t < PHASES.play) return 'wait'
  return t < PHASES.play + SETTLE ? 'run' : 'pass'
}

/**
 * Reads how many of the digest's digits the intro has written at `t`, and
 * whether they show as matching.
 */
export function digitsAt(t: number): { matched: boolean, revealed: number } {
  const share = (t - PHASES.open) / (PHASES.digest - PHASES.open - SETTLE)
  return {
    matched  : t >= PHASES.digest - SETTLE,
    revealed : t < PHASES.open ? 0 : Math.round(clamp(share, 0, 1) * RUN.digest.length)
  }
}

/**
 * Reads the window's strength at `t`, fading in as it opens and out before it
 * closes.
 */
export function windowAt(t: number): number {
  if (t < PHASES.open) return t / PHASES.open
  return t > PHASES.hold ? Math.max(0, 1 - (t - PHASES.hold) / (PHASES.close - PHASES.hold)) : 1
}

/**
 * Reads the veil over the screen at `t`, which lifts as the reset fades in.
 */
export const veilAt = (t: number): number =>
  t < PHASES.reset ? 1 - (t - PHASES.digest) / (PHASES.reset - PHASES.digest) : 0

/**
 * Reads whether the log line shows at `t`, once the return's check matches.
 */
export const loggedAt = (t: number): boolean => t >= PHASES.play + SETTLE

/**
 * Describes step `step` of the recording for a screen reader.
 */
export function describe(step: number, recording: readonly Recorded[] = RECORDING): string {
  return `Press ${count(step)} of ${count(recording.length - 1)}, ${pressName(recording[step]!.press)}`
}

/**
 * Splits the digest into lines of sixteen digits.
 */
export const DIGEST_LINES: readonly string[] = RUN.digest.match(/.{16}/gu)!
