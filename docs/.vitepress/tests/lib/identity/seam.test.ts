import { describe, expect, it } from 'vitest'

import { IDENTITY, hexOf } from '../../../lib/identity/identity.ts'
import * as seam           from '../../../lib/identity/seam.ts'

describe('FILLED', () => {
  it('steps through the trail in the order Blue walks it and then every dot still ahead, no dot in ink', () => {
    const steps = seam.FILLED.filter(dot => dot.kind === 'trail').map(dot => (dot as Extract<typeof dot, { kind: 'trail' }>).step)
    const kinds = seam.FILLED.map(dot => dot.kind)

    expect(steps).toStrictEqual(steps.toSorted((a, b) => a - b))
    expect(kinds.lastIndexOf('trail')).toBeLessThan(kinds.indexOf('ahead'))
    expect(new Set(kinds)).toStrictEqual(new Set(['ahead', 'trail']))
  })
})

describe('keyOf', () => {
  it.each(['light', 'dark'] as const)('keys the trail on the %s ground from its oldest third to the dot still ahead', scheme => {
    const { ahead, thirds } = IDENTITY.logo[scheme]

    expect(seam.keyOf(scheme).map(entry => entry.hex)).toStrictEqual([...thirds, ahead].map(token => hexOf(token as never)))
    expect(seam.keyOf(scheme).map(entry => entry.what))
      .toStrictEqual(['The first third, oldest', 'The middle third', 'The last third, newest', 'The dot still ahead'])
  })
})

describe('seamWords', () => {
  it.each([
    [0, 'The dark ground alone'],
    [100, 'The light ground alone'],
    [62, '62% on the light ground, 38% on the dark']
  ])('reads the seam at %d as %s', (at, words) => {
    expect(seam.seamWords(at)).toBe(words)
  })
})

describe('NUDGE', () => {
  it('starts and settles in the middle of the strip', () => {
    expect([seam.NUDGE[0], seam.NUDGE.at(-1)]).toStrictEqual([(seam.SEAM - 1) / 2, (seam.SEAM - 1) / 2])
  })
})
