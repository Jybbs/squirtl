import RELEASE                   from '../rendered/release.json' with { type: 'json' }
import { type Random, seeded }   from '../game/random.ts'
import { type Agent, COMMITTED } from '../results/results.ts'
import { fixed }                 from '../widgets/numbers.ts'

/**
 * One tar of the made-up release as its manifest lists it, the run's agent,
 * whether it trained along the curriculum, its name, and its seed, beside the
 * asset GitHub attaches it under, its size in megabytes, and its SHA-256
 * digest.
 */
export interface Tar {
  agent      : Agent
  asset      : string
  curriculum : boolean
  megabytes  : number
  name       : string
  seed       : number
  sha256     : string
}

/**
 * The tag of the made-up release.
 */
export const TAG = '0.2.0'

/**
 * The name of the demonstration every curriculum run in `docs/runs/` follows.
 */
export const DEMONSTRATION = '20261108T172406.446468Z'

/**
 * The name of the search `docs/runs/` commits, which the release attaches as
 * a demonstration rather than a trained run.
 */
export const SEARCH = '20261113T225532.465776Z'

/**
 * The name of the run the release plays where no selection names one, as
 * `ReleaseSettings` declares it.
 */
export const RECOMMENDED = RELEASE.recommended_run

/**
 * The digits a SHA-256 digest is written in.
 */
export const DIGITS = 64

/**
 * Draws a made-up SHA-256 digest in hexadecimal from `random`.
 */
export function hex(random: Random): string {
  return Array.from({ length: DIGITS }, () => Math.floor(random() * 16).toString(16)).join('')
}

/**
 * Sets `value` megabytes to one decimal place beside the unit.
 */
export function megabytes(value: number): string {
  return `${fixed(value, 1)} MB`
}

/**
 * The release's tars, each trained run `docs/runs/` commits in the order of
 * its name and then each demonstration, the run they follow and the search,
 * the sizes and the digests made up.
 */
const TARS: readonly Tar[] = (() => {
  const random = seeded(38)
  const packed = (run: Omit<Tar, 'asset' | 'megabytes' | 'sha256'>, size: number): Tar =>
    ({ ...run, asset: `${run.name}.tar.zst`, megabytes: size, sha256: hex(random) })

  return [
    ...COMMITTED.runs.map(({ agent, curriculum, name, seed }) =>
      packed({ agent, curriculum, name, seed }, Math.round(28 + random() * 14) / 10)),
    packed({ agent: 'ppo', curriculum: false, name: DEMONSTRATION, seed: 6 }, 0.4),
    packed({ agent: 'dqn', curriculum: false, name: SEARCH, seed: 2 }, 0.1)
  ]
})()

/**
 * Each trained run the release attaches, in the order of its name.
 */
export const RUNS = TARS.slice(0, COMMITTED.runs.length)

/**
 * Each demonstration, the run the trained runs follow and the search, in the
 * order of its name.
 */
export const DEMONSTRATIONS = TARS.slice(COMMITTED.runs.length)

/**
 * The time of day a run's name records, the part of it after the date.
 */
export function timeOf(name: string): string {
  return name.slice('YYYYMMDDT'.length)
}
