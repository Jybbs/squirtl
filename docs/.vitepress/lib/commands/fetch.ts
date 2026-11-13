import { clamp } from '@vueuse/core'

import { seeded }                           from '../game/random.ts'
import { DIGITS, RUNS, TAG, type Tar, hex } from './release.ts'

/**
 * Where a digit of one digest stands, compared with the other two and agreeing
 * or differing, or not yet compared.
 */
export type Agreement = 'agree' | 'differ' | 'open'

/**
 * Where one run of the selection stands: fetched into `data/runs/`, refused,
 * never reached once an earlier run is refused, being fetched, or waiting.
 */
export type Mark = 'done' | 'fail' | 'never' | 'now' | 'waiting'

/**
 * One of the three digests a tar is checked against, the one its download
 * hashes to, the one GitHub carries for its asset, and the one the manifest
 * records.
 */
export type Source = 'download' | 'github' | 'manifest'

/**
 * The command the widget runs, which selects the deep Q-network's runs.
 */
export const COMMAND = 'squirtl fetch --agent dqn'

/**
 * The runs `COMMAND` matches, every trained run of the deep Q-network in the
 * order of its name.
 */
export const MATCHED: readonly Tar[] = RUNS.filter(run => run.agent === 'dqn')

/**
 * The run whose tar the release altered after it was packed, so the digest
 * GitHub carries for its asset matches what downloads and the one the
 * manifest records does not.
 */
export const ALTERED = MATCHED[2]!

/**
 * Each digest a tar is checked against, by the name a reader reads for it.
 */
export const SOURCES: readonly { name: string, source: Source }[] = [
  { name: 'The download', source: 'download' },
  { name: 'GitHub’s asset', source: 'github' },
  { name: 'The manifest', source: 'manifest' }
]

/**
 * The beats each run takes: its download, a digit of the digests compared on
 * each beat after it, and the beats it holds once every digit is compared.
 */
export const BEATS = { digits: DIGITS, download: 10, hold: 4 } as const

/**
 * The beats one run takes in full.
 */
const SPAN = BEATS.download + BEATS.digits + BEATS.hold

/**
 * The made-up digest the altered tar hashes to, drawn from a generator of its
 * own.
 */
const TAMPERED = hex(seeded(59))

/**
 * The fetch of `MATCHED` at one beat: the run it is fetching, how much of its
 * tar has arrived, and how many digits of its digests are compared, beside
 * whether the release's tar of `ALTERED` was altered after it was packed, in
 * which case the fetch exits there.
 */
export class Fetching {
  altered = false
  at      = 0

  /**
   * The beats the whole fetch takes.
   */
  get beats(): number {
    return (this.last + 1) * SPAN
  }

  /**
   * The count of digits compared.
   */
  get compared(): number {
    return clamp(this.into - BEATS.download, 0, BEATS.digits)
  }

  /**
   * Whether the fetch has played to its end.
   */
  get done(): boolean {
    return this.at >= this.beats
  }

  /**
   * Whether the run's check has ended, every digit compared or the first
   * differing digit reached.
   */
  get ended(): boolean {
    return this.compared >= BEATS.digits || (this.first >= 0 && this.compared > this.first)
  }

  /**
   * Whether the run's check has ended on a differing digit, and with it the
   * fetch.
   */
  get failed(): boolean {
    return this.ended && this.first >= 0
  }

  /**
   * The index of the first digit where the download differs from the
   * manifest, or `-1` where the two agree.
   */
  get first(): number {
    const { download, manifest } = this.digests()
    return [...download].findIndex((digit, i) => digit !== manifest[i])
  }

  /**
   * The index of the run being fetched.
   */
  get index(): number {
    return Math.min(this.last, Math.floor(Math.min(this.at, this.beats - 1) / SPAN))
  }

  /**
   * The beats spent on the run being fetched.
   */
  get into(): number {
    return Math.min(this.at, this.beats) - this.index * SPAN
  }

  /**
   * The index of the last run the fetch reaches.
   */
  get last(): number {
    return this.altered ? MATCHED.indexOf(ALTERED) : MATCHED.length - 1
  }

  /**
   * The run being fetched.
   */
  get run(): Tar {
    return MATCHED[this.index]!
  }

  /**
   * The share of the run's tar that has arrived.
   */
  get share(): number {
    return Math.min(1, this.into / BEATS.download)
  }

  /**
   * Moves the fetch one beat.
   */
  advance() {
    this.at = Math.min(this.beats, this.at + 1)
  }

  /**
   * The three digests of the run being fetched, the altered tar's download and
   * asset agreeing with each other and differing from its manifest.
   */
  digests(): Record<Source, string> {
    const { sha256 } = this.run
    const download   = this.altered && this.run.name === ALTERED.name ? TAMPERED : sha256

    return { download, github: download, manifest: sha256 }
  }

  /**
   * Lists the digits of the digest `source` names, where each stands in the
   * comparison, the download's shown only once its tar has arrived.
   */
  digits(source: Source): { agreement: Agreement, digit: string }[] {
    const digests = this.digests()
    const shown   = source !== 'download' || this.share >= 1

    return [...digests[source]].map((digit, i) => ({
      agreement : i >= this.compared ? 'open'
                : digests.download[i] === digests.manifest[i] && digests.github[i] === digests.manifest[i] ? 'agree'
                : 'differ',
      digit     : shown ? digit : '·'
    }))
  }

  /**
   * Plays the fetch to its end.
   */
  finish() {
    this.at = this.beats
  }

  /**
   * Marks where each run of `MATCHED` stands.
   */
  marks(): Mark[] {
    return MATCHED.map((_, i) =>
      i < this.index ? 'done'
        : i === this.index ? this.failed ? 'fail' : this.ended ? 'done' : 'now'
        : i > this.last ? 'never' : 'waiting')
  }

  /**
   * Starts the fetch over from its first beat.
   */
  reset() {
    this.at = 0
  }

  /**
   * Spells what the fetch is doing, the error `squirtl fetch` exits on where
   * the digests differ, or the directory it logs once a run is fetched.
   */
  verdict(): string {
    const { download, github, manifest } = this.digests()

    return this.failed
      ? `The tar of ${this.run.name} in the release ${TAG} has the SHA-256 digest ${download}, `
        + `where its asset carries sha256:${github} and the manifest records ${manifest}`
      : this.ended ? `Fetched data/runs/${this.run.name}`
      : this.share < 1 ? `Downloading ${this.run.asset}`
      : 'Comparing the three digests'
  }
}

/**
 * The longest line the fetch spells, the error it exits on at the altered
 * tar, which the widget reserves the height of.
 */
export const LONGEST = (() => {
  const fetching = new Fetching()
  fetching.altered = true
  fetching.finish()
  return fetching.verdict()
})()
