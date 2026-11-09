import { describe, expect, it } from 'vitest'

import * as watching from '../../../lib/commands/watch.ts'

describe('RECORDING', () => {
  it('opens on the reset and ends on the starter’s return', () => {
    expect([watching.RECORDING[0], watching.returned(watching.RECORDING.at(-1)!.total), watching.LAST])
      .toStrictEqual([{ press: null, total: 0 }, '0.9150', 163])
  })
})

describe('the phases', () => {
  const { close, digest, hold, open, play, reset } = watching.PHASES

  it.each([
    [0, 'wait', 'wait'],
    [open, 'run', 'wait'],
    [digest - 300, 'pass', 'wait'],
    [play, 'pass', 'run'],
    [play + 500, 'pass', 'pass']
  ] as const)('stands each check at %f', (t, intro, ending) => {
    expect([watching.introAt(t), watching.endingAt(t)]).toStrictEqual([intro, ending])
  })

  it('writes the intro’s digits as the window opens and matches them before the reset', () => {
    expect([watching.digitsAt(0), watching.digitsAt(open + 500), watching.digitsAt(digest)]).toStrictEqual([
      { matched: false, revealed: 0 }, { matched: false, revealed: 32 }, { matched: true, revealed: 64 }
    ])
  })

  it('fades the window in, holds it, and fades it out before it closes', () => {
    expect([open / 2, play, hold + 200, close].map(at => watching.windowAt(at))).toStrictEqual([0.5, 1, 0.5, 0])
  })

  it('lifts the veil over the reset, and logs the return once its check matches', () => {
    expect([watching.veilAt(digest), watching.veilAt(reset), watching.loggedAt(play), watching.loggedAt(play + 500)])
      .toStrictEqual([1, 0, false, true])
  })

  it('reads the step a time reaches and the time that stands on a step', () => {
    expect([watching.stepAt(0), watching.stepAt(watching.timeOf(40)), watching.stepAt(close)]).toStrictEqual([0, 40, 163])
  })

  it('splits the digest into four lines of sixteen and names each press', () => {
    expect([watching.DIGEST_LINES.length, watching.describe(1)]).toStrictEqual([4, 'Press 1 of 163, Right'])
  })
})
