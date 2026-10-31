import fs   from 'node:fs'
import path from 'node:path'

import { renderAsync } from '@resvg/resvg-js'

import { docsDir }                               from '../config/paths.ts'
import { SECTIONS, type Section, sectionOf }     from '../config/sections.ts'
import { IDENTITY }                              from '../identity/identity.ts'
import { type CardPage, type Edition, cardPath } from './cards.ts'
import { drawSectionCard }                       from './section-card.ts'
import { drawSiteCard }                          from './site-card.ts'

/**
 * The folder under `docs/` holding the TrueType faces a card's words are set
 * in, which the renderer loads in place of the system's fonts.
 */
const FACES = path.join('.vitepress', 'lib', 'cards', 'faces')

/**
 * The cards one build draws, gathering each page as the build renders its head
 * and drawing every card once the build ends.
 */
export class Cards {
  readonly #facts   : Edition
  readonly #metaUrl : string
  readonly #pages   : CardPage[] = []

  constructor(facts: Edition, metaUrl: string) {
    this.#facts   = facts
    this.#metaUrl = metaUrl
  }

  /**
   * Adds `page` to the pages the build renders.
   */
  add(page: CardPage): void {
    this.#pages.push(page)
  }

  /**
   * Draws the card of every page added so far under `outDir`.
   *
   * Returns:
   *   The path of each card written, under `outDir`.
   */
  render(outDir: string): Promise<string[]> {
    return renderCards(this.#facts, this.#metaUrl, outDir, this.#pages)
  }
}

/**
 * Draws the card of every page in `pages` as a PNG under `outDir`, at the path
 * `cardPath` gives it, a page of a section taking its section's card and every
 * other page the site's, which the front page and the page at a missing address
 * share, so it is written once.
 *
 * Args:
 *   facts    : The version and the host each card's edition plate names.
 *   metaUrl  : The `import.meta.url` of the module calling, which the checkout
 *     holding the faces is found from.
 *   outDir   : The folder the built site is written to.
 *   pages    : The pages the build rendered.
 *   sections : The sections the site carries.
 *
 * Returns:
 *   The path of each card written, under `outDir`.
 */
export async function renderCards(
  facts    : Edition,
  metaUrl  : string,
  outDir   : string,
  pages    : readonly CardPage[],
  sections : readonly Section[] = SECTIONS
): Promise<string[]> {
  const font = {
    defaultFontFamily : IDENTITY.faces.body.family,
    fontDirs          : [path.join(docsDir(metaUrl), FACES)],
    loadSystemFonts   : false
  }

  const cards = new Map(pages.map((page): [string, string] => {
    const section = sectionOf(page, sections)
    const drawing = section ? drawSectionCard(facts, section, page.title, sections) : drawSiteCard(facts)
    return [cardPath(page), drawing]
  }))

  await Promise.all([...cards].map(async ([file, svg]) => {
    const target = path.join(outDir, file)
    const image  = await renderAsync(svg, { font })
    await fs.promises.mkdir(path.dirname(target), { recursive: true })
    await fs.promises.writeFile(target, image.asPng())
  }))

  return [...cards.keys()]
}
