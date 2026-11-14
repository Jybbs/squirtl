import { describe, expect, it } from 'vitest'

import { IDENTITY, sectionHue } from '../../../lib/identity/identity.ts'
import { SCHEMES }              from '../../../lib/identity/palette.ts'
import { logoColors }           from '../../../lib/marks/logo.ts'
import * as start               from '../../../lib/readme/start.ts'

/**
 * Reads the centers of the dots of the trail `svg` draws, each of radius 6, in
 * the order it draws them.
 */
const dotsOf = (svg: string): [number, number][] =>
  [...svg.matchAll(/<circle cx="([\d.]+)" cy="([\d.]+)" r="6"/gu)].map(([, x, y]) => [Number(x), Number(y)])

describe('drawStartCard', () => {
  it.each(start.START_CARDS.flatMap(card => SCHEMES.map(scheme => [card.word, scheme, card] as const)))(
    'draws %s in %s on its section’s Shade 1 with its word in the section’s mark',
    (word, scheme, card) => {
      const hue = sectionHue(card.folder)
      const svg = start.drawStartCard(card, scheme)

      expect(svg).toMatch(/^<svg xmlns="http:\/\/www\.w3\.org\/2000\/svg" width="260" height="150" /u)
      expect(svg).toContain(`aria-label="${word}"`)
      expect(svg).toContain(`fill="${IDENTITY.hues[hue][scheme].shades[0]}"/>`)
      expect(svg).toContain(`fill="${IDENTITY.marks[hue][scheme]}"`)
      expect(svg).toContain(`fill="${logoColors(scheme).block}"/>`)
    }
  )

  it.each([
    ['climbs a square between runs', 1, [100, 82, 64]],
    ['runs level', 0, [100]],
    ['descends a square between runs', -1, [100, 118, 136]]
  ] as const)('lays the trail of a card that %s', (_, rise, rows) => {
    const card = { folder: 'methods', rise, word: 'Check' } as const
    const dots = dotsOf(start.drawStartCard(card, 'light'))
    const ys   = [...new Set(dots.map(([, y]) => y))]

    expect(dots[0]).toStrictEqual([66, 100])
    expect(ys).toStrictEqual(rows)
  })

  it('sets every word in the cell the longest one fits, so the cards read at one size', () => {
    const cells = start.START_CARDS.map(card =>
      start.drawStartCard(card, 'light').match(/<circle [^>]*r="([\d.]+)"/u)![1])

    expect(new Set(cells).size).toBe(1)
  })

  it('shades the trail from the oldest third to the newest in the section’s ramp', () => {
    const [card] = start.START_CARDS as [start.StartCard]
    const hue    = sectionHue(card.folder)
    const steps  = IDENTITY.hues[hue].dark
    const fills  = [...start.drawStartCard(card, 'dark')
      .matchAll(/<circle cx="[\d.]+" cy="[\d.]+" r="6" fill="(#[0-9a-f]+)"/gu)]
      .map(([, fill]) => fill)

    expect([...new Set(fills)]).toStrictEqual([steps.shades[3], IDENTITY.marks[hue].dark, steps.pale])
  })
})

describe('startPath', () => {
  it('names each card’s file under the README’s assets for its word and its scheme', () => {
    expect(start.startPath(start.START_CARDS[2]!, 'dark')).toBe('assets/readme/run-dark.svg')
  })
})
