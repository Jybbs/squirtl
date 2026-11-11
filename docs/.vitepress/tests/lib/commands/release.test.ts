import { readFileSync, readdirSync } from 'node:fs'
import path                          from 'node:path'
import { describe, expect, it }      from 'vitest'

import * as release from '../../../lib/commands/release.ts'

/**
 * The folder holding the run each directory of `docs/runs/` commits.
 */
const RUNS = path.resolve(import.meta.dirname, '../../../../runs')

describe('DEMONSTRATION', () => {
  it('names the demonstration every committed curriculum run follows', () => {
    const followed = readdirSync(RUNS)
      .map(name => JSON.parse(readFileSync(path.join(RUNS, name, 'run.json'), 'utf8')).settings.curriculum.demonstration as string | null)
      .filter(shown => shown !== null)
      .map(shown => path.basename(shown))

    expect(new Set(followed)).toStrictEqual(new Set([release.DEMONSTRATION]))
  })
})

describe('RUNS', () => {
  it('lists every committed run in the order of its name, each tar named for it', () => {
    const names = readdirSync(RUNS).toSorted()

    expect([release.RUNS.map(run => run.name), release.RUNS.map(run => run.asset)]).toStrictEqual([
      names, names.map(name => `${name}.tar.zst`)
    ])
  })

  it('records a digest of sixty-four hexadecimal digits for every tar', () => {
    expect([...release.RUNS, ...release.DEMONSTRATIONS].every(run => /^[0-9a-f]{64}$/u.test(run.sha256))).toBe(true)
  })
})

describe('RECOMMENDED', () => {
  it('names one of the trained runs', () => {
    expect(release.RUNS.map(run => run.name)).toContain(release.RECOMMENDED)
  })
})

describe('megabytes', () => {
  it.each([[3.24, '3.2 MB'], [0.4, '0.4 MB']])('sets %d megabytes as %s', (value, text) => {
    expect(release.megabytes(value)).toBe(text)
  })
})

describe('timeOf', () => {
  it('reads the time of day a run’s name records', () => {
    expect(release.timeOf('20261108T230636.598162Z')).toBe('230636.598162Z')
  })
})
