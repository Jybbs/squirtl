import { describe, expect, it, vi } from 'vitest'

import { CARD }     from '../../../lib/cards/cards.ts'
import * as head    from '../../../lib/config/head.ts'
import { IDENTITY } from '../../../lib/identity/identity.ts'
import { FACTS }    from '../../common/facts.ts'
import { METHODS }  from '../../common/sections.ts'

vi.mock('../../../lib/config/sections.ts', async original => {
  const sections = await original<typeof import('../../../lib/config/sections.ts')>()
  return { ...sections, sectionOf: (page: never) => sections.sectionOf(page, [METHODS]) }
})

/**
 * The site data a case's head reads its language from.
 */
const SITE = { lang: 'en-US' }

/**
 * Reads each entry of a head as its tag and the attribute naming it beside the
 * value it carries.
 */
function tags(entries: ReturnType<typeof head.pageHead>): Record<string, string> {
  return Object.fromEntries(entries.map(([tag, attributes, body]) => {
    const name = attributes['property'] ?? attributes['name'] ?? attributes['rel'] ?? attributes['type']
    return [`${tag} ${name}`, attributes['content'] ?? attributes['href'] ?? body ?? '']
  }))
}

describe('pageUrl', () => {
  it.each([
    ['index.md', 'https://squirtl.fyi/'],
    ['methods/index.md', 'https://squirtl.fyi/methods/'],
    ['methods/agent.md', 'https://squirtl.fyi/methods/agent'],
    ['404.md', 'https://squirtl.fyi/404']
  ])('serves %s at %s', (relativePath, url) => {
    expect(head.pageUrl(FACTS.homepage, relativePath)).toBe(url)
  })
})

describe('pageHead', () => {
  it('describes the front page as the website and shows the site card', () => {
    const page = { relativePath: 'index.md', title: 'SquiRtL' } as never
    const meta = tags(head.pageHead({ description: 'Plays.', pageData: page, siteData: SITE }, FACTS))

    expect(meta).toMatchObject({
      'link canonical'         : 'https://squirtl.fyi/',
      'meta og:image'          : 'https://squirtl.fyi/cards/site.png',
      'meta og:image:alt'      : `${IDENTITY.name}, a deep Q-network that learns the walk to Oak’s lab.`,
      'meta og:image:height'   : String(CARD.height),
      'meta og:image:type'     : 'image/png',
      'meta og:image:width'    : String(CARD.width),
      'meta og:locale'         : 'en_US',
      'meta og:title'          : IDENTITY.name,
      'meta og:type'           : 'website',
      'meta og:url'            : 'https://squirtl.fyi/',
      'meta twitter:card'      : 'summary_large_image',
      'meta twitter:image'     : 'https://squirtl.fyi/cards/site.png',
      'meta twitter:image:alt' : `${IDENTITY.name}, a deep Q-network that learns the walk to Oak’s lab.`
    })
    expect(JSON.parse(meta['script application/ld+json']!)).toStrictEqual({
      '@context'    : 'https://schema.org',
      '@type'       : 'WebSite',
      'description' : 'Plays.',
      'inLanguage'  : 'en-US',
      'name'        : IDENTITY.name,
      'url'         : 'https://squirtl.fyi/'
    })
  })

  it('describes every other page as an article on the website, naming the section that holds it', () => {
    const page = { relativePath: 'methods/agent.md', title: 'The Agent' } as never
    const meta = tags(head.pageHead({ description: 'How it learns.', pageData: page, siteData: SITE }, FACTS))

    expect([meta['meta og:type'], meta['meta og:title'], meta['meta og:image'], meta['meta og:image:alt']])
      .toStrictEqual([
        'article', 'The Agent', 'https://squirtl.fyi/cards/methods/agent.png',
        `The Agent, a page of the Methods section of ${IDENTITY.name}`
      ])
    expect(JSON.parse(meta['script application/ld+json']!)).toMatchObject({
      '@type'    : 'TechArticle',
      'headline' : 'The Agent',
      'isPartOf' : { '@type': 'WebSite', 'name': IDENTITY.name, 'url': 'https://squirtl.fyi/' },
      'url'      : 'https://squirtl.fyi/methods/agent'
    })
  })
})

describe('siteHead', () => {
  it('loads every face through one Google Fonts request and names the favicon and the site', () => {
    const meta = tags(head.siteHead(FACTS))

    expect(meta['link stylesheet']).toBe(
        'https://fonts.googleapis.com/css2?'
      + Object.values(IDENTITY.faces).map(face => `family=${face.query}`).join('&')
      + '&display=swap'
    )
    expect([meta['link icon'], meta['meta og:site_name']]).toStrictEqual(['/favicon.svg', IDENTITY.name])
  })
})
