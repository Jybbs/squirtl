import { describe, expect, it } from 'vitest'

import * as fetch from '../../../lib/commands/fetch.ts'

/**
 * Plays a fresh fetch `beats` beats, of the release as packed or of the one
 * whose tar of `fetch.ALTERED` was altered.
 */
function played(beats: number, altered = false): fetch.Fetching {
  const fetching   = new fetch.Fetching()
  fetching.altered = altered
  for (let beat = 0; beat < beats; beat++) fetching.advance()
  return fetching
}

/**
 * The beats one run takes in full.
 */
const SPAN = fetch.BEATS.download + fetch.BEATS.digits + fetch.BEATS.hold

describe('MATCHED', () => {
  it('selects the deep Q-network’s runs alone', () => {
    expect(fetch.MATCHED.map(run => run.agent)).toStrictEqual(['dqn', 'dqn', 'dqn', 'dqn', 'dqn'])
  })
})

describe('Fetching', () => {
  it('downloads its first tar before it shows that tar’s digest', () => {
    const fetching = played(5)

    expect([fetching.verdict(), fetching.digits('download')[0]!.digit, fetching.marks()[0]]).toStrictEqual([
      `Downloading ${fetch.MATCHED[0]!.asset}`, '·', 'now'
    ])
  })

  it('compares the three digests a digit a beat once its tar has arrived', () => {
    const fetching = played(fetch.BEATS.download + 3)

    expect([fetching.verdict(), fetching.digits('manifest').map(digit => digit.agreement).slice(0, 4)]).toStrictEqual([
      'Comparing the three digests', ['agree', 'agree', 'agree', 'open']
    ])
  })

  it('fetches every run it matches where the release is as packed', () => {
    const fetching = played(SPAN * fetch.MATCHED.length)

    expect([fetching.done, fetching.failed, fetching.verdict(), fetching.marks()]).toStrictEqual([
      true, false, `Fetched data/runs/${fetch.MATCHED.at(-1)!.name}`, ['done', 'done', 'done', 'done', 'done']
    ])
  })

  it('plays to its end at once as it finishes, and starts over as it resets', () => {
    const fetching = new fetch.Fetching()

    fetching.finish()
    const finished = fetching.done
    fetching.reset()

    expect([finished, fetching.at, fetching.done]).toStrictEqual([true, 0, false])
  })
})

describe('Fetching at the altered tar', () => {
  it('compares the altered tar’s digests before it exits on them', () => {
    const fetching = played(SPAN * fetch.MATCHED.indexOf(fetch.ALTERED) + fetch.BEATS.download, true)

    expect([fetching.run.name, fetching.ended, fetching.verdict()]).toStrictEqual([
      fetch.ALTERED.name, false, 'Comparing the three digests'
    ])
  })

  it('exits at the altered tar on the error the command prints, never reaching the runs after it', () => {
    const fetching                       = played(SPAN * fetch.MATCHED.length, true)
    const { download, github, manifest } = fetching.digests()

    expect([fetching.done, fetching.failed, fetching.marks(), download === github, download === manifest]).toStrictEqual([
      true, true, ['done', 'done', 'fail', 'never', 'never'], true, false
    ])
    expect([fetching.verdict(), fetch.LONGEST]).toStrictEqual(Array.from({ length: 2 }, () =>
      `The tar of ${fetch.ALTERED.name} in the release 0.2.0 has the SHA-256 digest ${download}, `
      + `where its asset carries sha256:${github} and the manifest records ${manifest}`))
  })

  it('marks the digits where the altered download differs from the manifest', () => {
    const fetching               = played(SPAN * fetch.MATCHED.length, true)
    const { download, manifest } = fetching.digests()
    const differ                 = [...download].filter((digit, i) => digit !== manifest[i]).length

    expect([
      fetching.digits('github').filter(digit => digit.agreement === 'differ').length,
      fetching.digits('github').filter(digit => digit.agreement === 'agree').length
    ]).toStrictEqual([differ, fetch.BEATS.digits - differ])
  })
})
