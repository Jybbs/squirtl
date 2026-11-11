import { describe, expect, it } from 'vitest'

import EVENTS     from '../../../lib/rendered/events.json' with { type: 'json' }
import * as flags from '../../../lib/game/flags.ts'

describe('eventFlags and milestones', () => {
  it('names each event flag in the order the package declares the events, each with the term it pays', () => {
    expect(flags.eventFlags.map(each => [each.flag, each.term])).toStrictEqual([
      ['followed', 'milestone'],
      ['starter', 'starter'],
      ['appeared', 'milestone'],
      ['asked', 'milestone']
    ])
    expect(flags.eventFlags.map(each => each.term)).toStrictEqual(EVENTS.map(event => event.term))
  })

  it('reads the milestones as the flags whose events pay one', () => {
    expect(flags.milestones).toStrictEqual(['followed', 'appeared', 'asked'])
  })
})
