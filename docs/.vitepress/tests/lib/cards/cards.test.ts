import { describe, expect, it } from 'vitest'

import * as cards   from '../../../lib/cards/cards.ts'
import { IDENTITY } from '../../../lib/identity/identity.ts'
import { FACTS }    from '../../common/facts.ts'

describe('cardPath', () => {
  it.each([
    [{ relativePath: 'index.md' }, 'cards/site.png'],
    [{ isNotFound: true, relativePath: '404.md' }, 'cards/site.png'],
    [{ relativePath: 'methods/agent.md' }, 'cards/methods/agent.png']
  ])('gives %o the card %s', (page, path) => {
    expect(cards.cardPath(page)).toBe(path)
  })
})

describe('splitInTwo', () => {
  it.each([
    [IDENTITY.tagline, ['A deep Q-network that learns', 'the walk to Oak’s lab.']],
    ['one two three four', ['one two', 'three four']],
    ['aa b cc', ['aa', 'b cc']],
    ['alone', ['alone', '']]
  ])('splits %s at the space that balances its two lines', (text, lines) => {
    expect(cards.splitInTwo(text)).toEqual(lines)
  })
})

describe('wrapCard', () => {
  it.each(['dark', 'light'] as const)('wraps a %s card at the size a shared link shows', scheme => {
    expect(cards.wrapCard('<g/>', scheme)).toBe(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">'
      + `<rect width="1200" height="630" fill="${IDENTITY.tones[scheme].ground}"/><g/></svg>`
    )
  })
})

describe('setLine', () => {
  it.each([
    ['Oak’s lab', {}, '>Oak’s lab</text>'],
    ['random <presses> & steps', {}, '>random &lt;presses&gt; &amp; steps</text>'],
    ['tagline', { italic: true }, ' font-style="italic">tagline</text>'],
    ['crumb', { face: 'code', spacing: 2.08 }, ' letter-spacing="2.1">crumb</text>']
  ] as const)('sets %s as one line of SVG text', (text, lettering, tail) => {
    const line = cards.setLine(text, { fill: '#121722', size: 25, x: 72, y: 96, ...lettering })
    expect(line.slice(-tail.length)).toBe(tail)
  })

  it.each(['body', 'code'] as const)('sets a line in the %s face’s stack', face => {
    expect(cards.setLine('words', { face, fill: '#121722', size: 25, x: 72, y: 96 }))
      .toContain(`font-family="${IDENTITY.faces[face].stack}"`)
  })
})

describe('setCaps', () => {
  it('sets capitals in the code face, tracked at the identity’s share of the size', () => {
    expect(cards.setCaps('Edition · squirtl.fyi', { fill: '#f3f4f7', size: 24, x: 72, y: 96 })).toBe(
        `<text x="72" y="96" font-family="${IDENTITY.faces.code.stack}" font-size="24" fill="#f3f4f7" `
      + 'letter-spacing="1.9">EDITION · SQUIRTL.FYI</text>'
    )
  })
})

describe('fitCell', () => {
  it.each([
    ['SquiRtL', 10, 430, 10],
    ['SquiRtL', 10, 200, 5.3],
    ['Environment', 9, 488, 7.6]
  ])('fits %s, at most %i a cell, into %i pixels at a cell of %d', (text, most, room, cell) => {
    expect(cards.fitCell(text, most, room)).toBe(cell)
  })
})

describe('drawPlate', () => {
  it.each(['dark', 'light'] as const)('frames the version and the host at the foot of a %s card', scheme => {
    const plate          = cards.drawPlate(FACTS, scheme)
    const { ink, quiet } = IDENTITY.tones[scheme]

    expect(plate).toMatch(/^<rect x="72" y="466" width="[\d.]+" height="92" rx="6" fill="none" /u)
    expect(plate).toContain(`stroke="${quiet}" stroke-width="2"/>`)
    expect(plate).toContain(`fill="${ink}" letter-spacing="1.9">EDITION · SQUIRTL.FYI</text>`)
    expect(plate).toMatch(/<circle [^>]* r="2\.6" /u)
  })

  it('sets the plate’s middle on the line a section card marks the sections on', () => {
    expect(cards.plateLine).toBe(512)
  })
})
