import { describe, expect, it } from 'vitest'

import EVENTS     from '../../../lib/rendered/events.json' with { type: 'json' }
import * as flags from '../../../lib/game/flags.ts'

describe('eventFlags and milestones', () => {
  it('names each event flag up to the default goal in the order the package declares the events, each with its index and the term it pays, and none past it', () => {
    expect(flags.eventFlags.map(each => [each.flag, each.index, each.term])).toStrictEqual([
      ['appeared', 0x27, 'milestone'],
      ['followed', 0x00, 'milestone'],
      ['asked', 0x21, 'milestone'],
      ['starter', 0x22, 'goal']
    ])
    expect(EVENTS.map(event => event.term)).toStrictEqual(['milestone', 'milestone', 'milestone', 'goal', null, null, null])
  })

  it('reads the milestones as the flags whose events pay one', () => {
    expect(flags.milestones).toStrictEqual(['appeared', 'followed', 'asked'])
  })
})
