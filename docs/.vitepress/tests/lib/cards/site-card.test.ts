import { describe, expect, it } from 'vitest'

import TOWN             from '../../../lib/art/town.json' with { type: 'json' }
import { drawSiteCard } from '../../../lib/cards/site-card.ts'
import { IDENTITY }     from '../../../lib/identity/identity.ts'
import { logoColors }   from '../../../lib/marks/logo.ts'
import { FACTS }        from '../../common/facts.ts'

/**
 * Counts the times `part` occurs in `svg`.
 */
const count = (svg: string, part: string): number => svg.split(part).length - 1

describe.each(['dark', 'light'] as const)('drawSiteCard in the %s scheme', scheme => {
  const svg        = drawSiteCard(FACTS, scheme)
  const { thirds } = logoColors(scheme)

  it('draws the card over Pallet Town', () => {
    expect(svg).toMatch(/^<svg xmlns="http:\/\/www\.w3\.org\/2000\/svg" width="1200" height="630" /u)
    expect(svg).toContain(`<rect width="1200" height="630" fill="${IDENTITY.tones[scheme].ground}"/>`)
    expect(svg).toContain(`<image href="${TOWN.image[scheme]}" x="542" y="34.`)
  })

  it('sets the tagline in two italic lines', () => {
    expect(svg).toContain('font-style="italic">A deep Q-network that learns</text>')
    expect(svg).toContain('font-style="italic">the walk to Oak’s lab.</text>')
  })

  it('fades the walk in thirds', () => {
    const halo = `stroke="${IDENTITY.tones[scheme].ground}" stroke-width="5" paint-order="stroke"`
    expect(thirds.map(hex => count(svg, `fill="${hex}" ${halo}`))).toEqual([5, 4, 4])
  })

  it('sets the R and the L in the newest third', () => {
    expect(count(svg, `r="6.0" fill="${thirds[2]}"`)).toBe(36)
  })
})

describe('drawSiteCard', () => {
  it('draws the dark card where no scheme is named', () => {
    expect(drawSiteCard(FACTS)).toBe(drawSiteCard(FACTS, 'dark'))
  })

  it('stands Blue in his block at the start of the walk and the Poké Ball at its end', () => {
    const svg = drawSiteCard(FACTS)
    expect(svg).toContain('<rect x="694.3" y="217.7" width="38.7" height="38.7" rx="10.6" fill="#7097df"/>')
    expect(svg).toContain('<circle cx="932.0" cy="393.0" r="21.8" fill="#121722"/>')
  })
})
