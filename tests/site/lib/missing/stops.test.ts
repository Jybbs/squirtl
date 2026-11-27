import { describe, expect, it } from 'vitest'

import { drawSectionCard } from '../../../../docs/.vitepress/lib/cards/section-card.ts'
import { drawSiteCard }    from '../../../../docs/.vitepress/lib/cards/site-card.ts'
import * as stops          from '../../../../docs/.vitepress/lib/missing/stops.ts'
import { FACTS }           from '../../common/facts.ts'
import { METHODS }         from '../../common/sections.ts'

/**
 * The text of the front page and of each section's overview, keyed by its path
 * under `docs/pages/` after a `./`.
 */
const OVERVIEWS = import.meta.glob<string>(['./index.md', './*/index.md'], {
  base   : '../../../../docs/pages',
  eager  : true,
  import : 'default',
  query  : '?raw'
})

describe('stopsOf', () => {
  it('leads back to the front page first, then to each section’s overview with its two lines', () => {
    const [front, methods] = stops.stopsOf([METHODS])

    const methodsStop = { label: 'Methods', link: '/methods/', note: 'What the agent learns, and how.' }

    expect([front!.link, front!.section, methods])
      .toStrictEqual(['/', undefined, expect.objectContaining(methodsStop)])
  })

  it('leads only to a page the site builds', () => {
    const files = stops.stopsOf().map(stop => `.${stop.link}index.md`)

    expect(files.filter(file => !Object.hasOwn(OVERVIEWS, file))).toStrictEqual([])
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
