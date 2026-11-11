import { describe, expect, it } from 'vitest'

import * as pack                                        from '../../../lib/commands/pack.ts'
import { DEMONSTRATIONS, RECOMMENDED, RUNS, type Tar } from '../../../lib/commands/release.ts'

/**
 * Plays a fresh pack `beats` beats.
 */
function played(beats: number): pack.Packing {
  const packing = new pack.Packing()
  for (let beat = 0; beat < beats; beat++) packing.advance()
  return packing
}

/**
 * Writes `line` as the manifest does once its tar is written.
 */
const filled = (line: pack.Line): string => line.tar ? `${line.text}${line.tar.sha256}"` : line.text

/**
 * The fields of `tar` the manifest records.
 */
const listed = ({ agent, curriculum, name, seed, sha256 }: Tar) => ({ agent, curriculum, name, seed, sha256 })

describe('ORDER', () => {
  it('packs each demonstration before the trained runs', () => {
    expect(pack.ORDER).toStrictEqual([...DEMONSTRATIONS, ...RUNS])
  })
})

describe('LINES', () => {
  it('writes manifest.json as the manifest dumps itself, filled with each digest', () => {
    const text = pack.LINES.map(line => filled(line)).join('\n')

    expect(JSON.parse(text)).toStrictEqual({
      demonstrations  : DEMONSTRATIONS.map(tar => listed(tar)),
      recommended_run : RECOMMENDED,
      runs            : RUNS.map(tar => listed(tar))
    })
    expect(text).toBe(JSON.stringify(JSON.parse(text), null, 2))
  })
})

describe('Packing', () => {
  it('reads the runs before it writes a tar', () => {
    const packing = new pack.Packing()

    expect([packing.head(), packing.log(), packing.first, pack.ORDER.some(tar => packing.packed(tar))]).toStrictEqual([
      `0 of ${pack.ORDER.length} tars written`, 'Reading the runs docs/runs/ lists', 0, false
    ])
  })

  it('writes a tar a beat, the lines shown following the digest filled last', () => {
    const packing = played(5)
    const focus   = pack.LINES.findIndex(line => line.tar?.name === pack.ORDER[4]!.name)

    expect([packing.log(), packing.packed(pack.ORDER[4]!), packing.packed(pack.ORDER[5]!)]).toStrictEqual([
      `Wrote dist/runs/${pack.ORDER[4]!.asset}`, true, false
    ])
    expect(focus - packing.first).toBe(pack.WINDOW / 2)
  })

  it('writes the manifest once every tar is written, showing the file’s last lines', () => {
    const packing = played(pack.ORDER.length + 5)

    expect([packing.done, packing.log(), packing.first]).toStrictEqual([
      true, `Wrote manifest.json beside ${pack.ORDER.length} tars, and squirtl pack prints dist/runs`,
      pack.LINES.length - pack.WINDOW
    ])
  })

  it('plays to its end at once as it finishes, and starts over as it resets', () => {
    const packing = new pack.Packing()

    packing.finish()
    const finished = packing.done
    packing.reset()

    expect([finished, packing.at]).toStrictEqual([true, 0])
  })
})
