import { describe, expect, it } from 'vitest'

import { drawSectionCard }                from '../../../lib/cards/section-card.ts'
import { SECTIONS, type Section, placed } from '../../../lib/config/sections.ts'
import { spriteMarkup }                   from '../../../lib/drawing/sprites.ts'
import { IDENTITY }                       from '../../../lib/identity/identity.ts'
import { FACTS }                          from '../../common/facts.ts'
import { METHODS }                        from '../../common/sections.ts'

/**
 * Three sections, which take Forest, Indigo, and Cerulean and the first three
 * badges the game awards in that order, the last with lines holding the
 * characters XML reads as markup.
 */
const THREE: readonly Section[] = [
  { about: ['Each command the package installs,', 'and every setting it takes.'], name: 'Commands' },
  METHODS,
  { about: ['Each run measured & set beside', 'random <presses>.'], name: 'Results' }
]

/**
 * The three sections as the site places them.
 */
const PLACED = placed(THREE)

describe('drawSectionCard', () => {
  it.each([
    { badge: 'Boulder', city: [736, 189], hue: 'forest', index: 0, spot: [664, 233] },
    { badge: 'Cascade', city: [960, 161], hue: 'indigo', index: 1, spot: [888, 205] },
    { badge: 'Thunder', city: [960, 357], hue: 'cerulean', index: 2, spot: [888, 169] }
  ] as const)('draws section $index in $hue around the $badge city', ({ badge, city, hue, index, spot }) => {
    const section = PLACED[index]!
    const tones   = IDENTITY.hues[hue].dark
    const color   = IDENTITY.marks[hue].dark
    const fills   = [tones.shades[1]!, tones.shades[2]!, color, tones.pale]
    const crumb   = `${section.name.toUpperCase()} · SECTION ${index + 1} OF 3`
    const svg     = drawSectionCard(FACTS, section, 'Page', THREE)

    expect(section).toMatchObject({ badge: { name: badge }, hue })
    expect(svg).toContain(`<circle cx="${city[0]}" cy="${city[1]}" r="22" fill="none" stroke="${tones.pale}"`)
    expect(svg).toContain(`<rect x="${spot[0] - 16}" y="${spot[1] - 16}" width="176" height="176" rx="28" `
                        + `fill="#121722" stroke="${color}" stroke-width="3"/>`)
    expect(svg).toContain(spriteMarkup(section.badge.grid, { fills, size: 9, x: spot[0], y: spot[1] }))
    expect(svg).toContain(`fill="${tones.text}" letter-spacing="2.1">${crumb}</text>`)
    expect(svg).toContain(`<filter id="faded-${hue}" `)
  })
})

describe('drawSectionCard, beside the map', () => {
  it.each([
    { index: 0, side: 'below', sign: 1 },
    { index: 1, side: 'below', sign: 1 },
    { index: 2, side: 'above', sign: -1 }
  ])('sets badge $index $side its city', ({ index, sign }) => {
    const svg  = drawSectionCard(FACTS, PLACED[index]!, 'Page', THREE)
    const ring = Number(/<circle cx="[\d.]+" cy="([\d.]+)" r="22"/u.exec(svg)![1])
    const box  = Number(/<rect x="[\d.]+" y="([\d.]+)" width="176"/u.exec(svg)![1])
    expect(Math.sign(box - ring)).toBe(sign)
  })

  it('marks the other cities faintly and each section on the edition line', () => {
    const svg = drawSectionCard(FACTS, PLACED[1]!, 'Page', THREE)
    expect(svg.split('rx="4" fill="none"')).toHaveLength(3)
    expect(svg.match(/<circle cx="[\d.]+" cy="512" r="\d"/gu)).toEqual([
      '<circle cx="1084" cy="512" r="4"',
      '<circle cx="1106" cy="512" r="7"',
      '<circle cx="1128" cy="512" r="4"'
    ])
  })

  it('escapes the characters XML reads as markup in a section’s lines', () => {
    const svg = drawSectionCard(FACTS, PLACED[2]!, 'Page', THREE)
    expect(svg).toContain('>Each run measured &amp; set beside</text>')
    expect(svg).toContain('>random &lt;presses&gt;.</text>')
  })

  it('counts the sections the site carries where none are passed', () => {
    expect(drawSectionCard(FACTS, PLACED[0]!, 'Page'))
      .toBe(drawSectionCard(FACTS, PLACED[0]!, 'Page', SECTIONS))
  })
})
