import { readFileSync, readdirSync } from 'node:fs'
import path                          from 'node:path'
import { describe, expect, it }      from 'vitest'

import * as release from '../../../lib/commands/release.ts'

/**
 * The folder holding the run each directory of `docs/runs/` commits.
 */
const RUNS = path.resolve(import.meta.dirname, '../../../../runs')

/**
 * Each run `docs/runs/` commits beside its name, in the order of its name.
 */
const COMMITTED = readdirSync(RUNS).toSorted().map(name => ({
  name,
  run: JSON.parse(readFileSync(path.join(RUNS, name, 'run.json'), 'utf8')) as {
    searches? : boolean
    settings  : { agent: { algorithm: string }, curriculum: { demonstration: string | null }, seed: number }
  }
}))

describe('DEMONSTRATION', () => {
  it('names the demonstration every committed curriculum run follows', () => {
    const followed = COMMITTED
      .map(({ run }) => run.settings.curriculum.demonstration)
      .filter(shown => shown !== null)
      .map(shown => path.basename(shown))

    expect(new Set(followed)).toStrictEqual(new Set([release.DEMONSTRATION]))
  })
})

describe('SEARCH', () => {
  it('names the one search docs/runs/ commits, its tar listing the agent, curriculum, and seed its record holds', () => {
    const tar = release.DEMONSTRATIONS.find(({ name }) => name === release.SEARCH)

    expect(
      COMMITTED
        .filter(({ run }) => run.searches)
        .map(({ name, run }) => [name, run.settings.agent.algorithm, run.settings.curriculum.demonstration !== null, run.settings.seed])
    ).toStrictEqual([[tar?.name, tar?.agent, tar?.curriculum, tar?.seed]])
  })
})

describe('DEMONSTRATIONS', () => {
  it('lists the followed run and the search in the order of its name', () => {
    expect(release.DEMONSTRATIONS.map(tar => tar.name)).toStrictEqual([release.DEMONSTRATION, release.SEARCH].toSorted())
  })
})

describe('RUNS', () => {
  it('lists every committed trained run in the order of its name, each tar named for it', () => {
    const names = COMMITTED.filter(({ run }) => !run.searches).map(({ name }) => name)

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
