import { describe, expect, it } from 'vitest'

import * as sees      from '../../../../lib/front/sees.ts'
import * as labels    from '../../../../lib/front/sees/labels.ts'
import { termMark }   from '../../../../lib/game/actors.ts'
import { eventFlags } from '../../../../lib/game/episode.ts'
import { MINUS }      from '../../../../lib/widgets/numbers.ts'

describe('captionsOf', () => {
  it('writes the shape of each entry beside the bytes it holds', () => {
    const observing = { ...sees.OBSERVING, frame: { height: 2, width: 3 }, grid: 5, stack: 4 }

    expect(labels.captionsOf(observing)).toStrictEqual({
      flags  : '7, in the order the opening sets them · 7 bytes',
      frames : '4 × 2 × 3, newest last · 24 bytes',
      grid   : '5 × 5, Blue at the center · 25 bytes'
    })
  })
})

describe('flagsOf', () => {
  it('sets each flag beside the mark of the term it pays, in the order the network reads the flags', () => {
    expect(labels.flagsOf().map(each => [each.flag, each.name, each.term, each.mark]))
      .toStrictEqual(eventFlags.map(each => [each.flag, each.name, each.term, termMark(each.term)]))
  })
})

describe('frameNamesOf', () => {
  it('names each frame from the oldest by the steps it lies back from the newest', () => {
    expect(labels.frameNamesOf({ ...sees.OBSERVING, stack: 3 })).toStrictEqual([
      { back: 2, label: 'The frame 2 steps before', tag: `t ${MINUS} 2` },
      { back: 1, label: 'The frame 1 step before', tag: `t ${MINUS} 1` },
      { back: 0, label: 'The frame of this step', tag: 't' }
    ])
  })
})

describe('pastOf', () => {
  it('names each flag past the default goal beside its index, in the order the network reads the flags', () => {
    expect(labels.pastOf()).toStrictEqual([
      { index: 0x23, name: 'Battled the rival' },
      { index: 0x39, name: 'Got Oak’s parcel' },
      { index: 0x25, name: 'Got the Pokédex' }
    ])
  })
})
