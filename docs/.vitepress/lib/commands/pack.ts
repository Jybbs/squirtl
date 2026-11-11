import { clamp } from '@vueuse/core'

import { count }                                       from '../widgets/numbers.ts'
import { DEMONSTRATIONS, RECOMMENDED, RUNS, type Tar } from './release.ts'

/**
 * One line of `manifest.json`, its text up to the digest where it records a
 * tar's, and the tar whose digest it records.
 */
export interface Line {
  text : string
  tar? : Tar
}

/**
 * The tars `squirtl pack` writes in the order it writes them, each
 * demonstration and then each trained run.
 */
export const ORDER: readonly Tar[] = [...DEMONSTRATIONS, ...RUNS]

/**
 * The count of lines of `manifest.json` the widget shows at once.
 */
export const WINDOW = 12

/**
 * The lines of the entry for `tar` in a list of tars, the last entry closing
 * without a comma.
 */
function entry(tar: Tar, last: boolean): Line[] {
  return [
    { text: '    {' },
    { text: `      "agent": "${tar.agent}",` },
    { text: `      "curriculum": ${tar.curriculum},` },
    { text: `      "name": "${tar.name}",` },
    { text: `      "seed": ${tar.seed},` },
    { tar: tar, text: '      "sha256": "' },
    { text: `    }${last ? '' : ','}` }
  ]
}

/**
 * The lines of a list of `tars` under `key`, closing with a comma where
 * another field follows.
 */
function listing(key: string, tars: readonly Tar[], comma: boolean): Line[] {
  return [
    { text: `  "${key}": [` },
    ...tars.flatMap((tar, i) => entry(tar, i === tars.length - 1)),
    { text: `  ]${comma ? ',' : ''}` }
  ]
}

/**
 * The lines of `manifest.json` as the manifest writes itself, two spaces to a
 * level and its fields in the order the manifest declares them.
 */
export const LINES: readonly Line[] = [
  { text: '{' },
  { text: `  "recommended_run": "${RECOMMENDED}",` },
  ...listing('demonstrations', DEMONSTRATIONS, true),
  ...listing('runs', RUNS, false),
  { text: '}' }
]

/**
 * The pack at one beat: the tars written into `dist/runs/` so far, a beat
 * each in `ORDER`, and then `manifest.json` beside them.
 */
export class Packing {
  at = 0

  /**
   * The tar written last, or `null` before the first.
   */
  get current(): Tar | null {
    return ORDER[Math.min(this.at, ORDER.length) - 1] ?? null
  }

  /**
   * Whether the pack has played to its end, the manifest written.
   */
  get done(): boolean {
    return this.at > ORDER.length
  }

  /**
   * The index of the first of the `WINDOW` lines shown, which keep the line
   * recording the digest of the tar written last near their middle.
   */
  get first(): number {
    const { current } = this
    const focus       = current === null ? 0 : LINES.findIndex(line => line.tar?.name === current.name)

    return clamp(focus - WINDOW / 2, 0, LINES.length - WINDOW)
  }

  /**
   * Moves the pack one beat, writing the next tar or, after the last, the
   * manifest.
   */
  advance() {
    this.at = Math.min(ORDER.length + 1, this.at + 1)
  }

  /**
   * Plays the pack to its end.
   */
  finish() {
    this.at = ORDER.length + 1
  }

  /**
   * Counts the tars written.
   */
  head(): string {
    return `${count(Math.min(this.at, ORDER.length))} of ${count(ORDER.length)} tars written`
  }

  /**
   * Spells what the pack has just written.
   */
  log(): string {
    const { current } = this

    return this.done ? `Wrote manifest.json beside ${count(ORDER.length)} tars, and squirtl pack prints dist/runs`
      : current === null ? 'Reading the runs docs/runs/ lists'
      : `Wrote dist/runs/${current.asset}`
  }

  /**
   * Whether the tar of `tar` is written.
   */
  packed(tar: Tar): boolean {
    return ORDER.findIndex(each => each.name === tar.name) < this.at
  }

  /**
   * Starts the pack over from its first beat.
   */
  reset() {
    this.at = 0
  }
}
