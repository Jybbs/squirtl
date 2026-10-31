import fs   from 'node:fs'
import path from 'node:path'

import { describe, expect, it } from 'vitest'

import { drawSectionCard } from '../../../lib/cards/section-card.ts'
import { drawSiteCard }    from '../../../lib/cards/site-card.ts'
import { pagesDir }        from '../../../lib/config/paths.ts'
import * as stops          from '../../../lib/missing/stops.ts'
import { FACTS }           from '../../common/facts.ts'
import { METHODS }         from '../../common/sections.ts'

describe('stopsOf', () => {
  it('leads back to the front page first, then to each section’s overview with its two lines', () => {
    const [front, methods] = stops.stopsOf([METHODS])

    const methodsStop = { label: 'Methods', link: '/methods/', note: 'What the agent learns, and how.' }

    expect([front!.link, front!.section, methods])
      .toStrictEqual(['/', undefined, expect.objectContaining(methodsStop)])
  })

  it('leads only to a page the site builds', () => {
    const files = stops.stopsOf().map(stop => path.join(pagesDir(import.meta.url), stop.link, 'index.md'))

    expect(files.filter(file => !fs.existsSync(file))).toStrictEqual([])
  })
})

describe('cardOf and markOf', () => {
  it('draws the site’s card and Blue in his block for the front page', () => {
    const [front] = stops.stopsOf([METHODS])

    expect([stops.cardOf(front!, FACTS), stops.markOf(front!)])
      .toStrictEqual([drawSiteCard(FACTS), expect.stringContaining('var(--color-block)')])
  })

  it('draws the section’s card and its badge in its hue for a section', () => {
    const [, methods] = stops.stopsOf([METHODS])
    const card        = drawSectionCard(FACTS, methods!.section!, 'Methods')

    expect([stops.cardOf(methods!, FACTS), stops.markOf(methods!)])
      .toStrictEqual([card, expect.stringContaining('var(--color-indigo-badge-')])
  })
})
