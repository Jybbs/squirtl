import type { HeadConfig, SiteData, TransformContext } from 'vitepress'

import { CARD, type CardPage, cardPath } from '../cards/cards.ts'
import { IDENTITY }                      from '../identity/identity.ts'
import type { ProjectFacts }             from './manifest.ts'
import { isFrontPage }                   from './pages.ts'
import { sectionOf }                     from './sections.ts'

/**
 * Writes the text a card's image is described by, the site's name and tagline
 * on the site's card and the page's title beside its section on a page's.
 */
function cardAlt(page: CardPage): string {
  const section = sectionOf(page)
  return section
       ? `${page.title}, a page of the ${section.name} section of ${IDENTITY.name}`
       : `${IDENTITY.name}, ${IDENTITY.tagline.charAt(0).toLowerCase()}${IDENTITY.tagline.slice(1)}`
}

/**
 * Writes `name` and `content` as a `<meta>` entry, under `property` for an Open
 * Graph name and under `name` for every other.
 */
const meta = (name: string, content: string | number): HeadConfig =>
  ['meta', { [name.startsWith('og:') ? 'property' : 'name']: name, content: String(content) }]

/**
 * Writes the entries a page's head carries for a shared link, meaning its Open
 * Graph and Twitter card tags, its canonical address, and its JSON-LD in the
 * site's language, the front page described as the website and every other
 * page as an article on it.
 */
export function pageHead(
  context : Pick<TransformContext, 'description' | 'pageData'> & { siteData: Pick<SiteData, 'lang'> },
  facts   : ProjectFacts
): HeadConfig[] {
  const { description, pageData, siteData } = context

  const front = isFrontPage(pageData.relativePath)
  const title = front ? IDENTITY.name : pageData.title
  const url   = pageUrl(facts.homepage, pageData.relativePath)
  const image = new URL(cardPath(pageData), facts.homepage).href
  const alt   = cardAlt(pageData)
  const site  = { '@type': 'WebSite', 'name': IDENTITY.name, 'url': facts.homepage }
  const graph = front
              ? {
                  ...site,
                  '@context'    : 'https://schema.org',
                  'description' : description,
                  'inLanguage'  : siteData.lang
                }
              : {
                  '@context'    : 'https://schema.org',
                  '@type'       : 'TechArticle',
                  'description' : description,
                  'headline'    : title,
                  'inLanguage'  : siteData.lang,
                  'isPartOf'    : site,
                  'url'         : url
                }

  return [
    ['link', { href: url, rel: 'canonical' }],
    meta('og:title', title),
    meta('og:description', description),
    meta('og:type', front ? 'website' : 'article'),
    meta('og:locale', siteData.lang.replace('-', '_')),
    meta('og:url', url),
    meta('og:image', image),
    meta('og:image:width', CARD.width),
    meta('og:image:height', CARD.height),
    meta('og:image:type', 'image/png'),
    meta('og:image:alt', alt),
    meta('twitter:card', 'summary_large_image'),
    meta('twitter:image', image),
    meta('twitter:image:alt', alt),
    ['script', { type: 'application/ld+json' }, JSON.stringify(graph)]
  ]
}

/**
 * Builds the address the page at `relativePath` serves at under `homepage`, an
 * `index.md` at its folder's address and every other page at its own path with
 * no extension, since the site serves clean addresses.
 */
export function pageUrl(homepage: string, relativePath: string): string {
  return new URL(relativePath.replace(/(?:^|(?<=\/))index\.md$/u, '').replace(/\.md$/u, ''), homepage).href
}

/**
 * Writes the entries every page's head shares, meaning the faces the site loads
 * from Google Fonts, the favicon, and the site's name for Open Graph.
 */
export function siteHead(facts: ProjectFacts): HeadConfig[] {
  const families = Object.values(IDENTITY.faces)
    .map(face => `family=${face.query}`)
    .join('&')

  return [
    ['link', { href: 'https://fonts.googleapis.com', rel: 'preconnect' }],
    ['link', { crossorigin: '', href: 'https://fonts.gstatic.com', rel: 'preconnect' }],
    ['link', { href: `https://fonts.googleapis.com/css2?${families}&display=swap`, rel: 'stylesheet' }],
    ['link', { href: `${facts.base}favicon.svg`, rel: 'icon', type: 'image/svg+xml' }],
    meta('og:site_name', IDENTITY.name)
  ]
}
