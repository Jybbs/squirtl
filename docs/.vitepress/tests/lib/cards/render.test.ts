import fs   from 'node:fs'
import path from 'node:path'

import { describe, expect } from 'vitest'

import { CARD }               from '../../../lib/cards/cards.ts'
import { Cards, renderCards } from '../../../lib/cards/render.ts'
import { test }               from '../../common/checkout.ts'
import { FACTS }              from '../../common/facts.ts'
import { METHODS }            from '../../common/sections.ts'

/**
 * The pages one build renders, the front page, the page a reader meets at a
 * missing address, a missing page at a path inside a section, and two pages of
 * that section.
 */
const PAGES = [
  { isNotFound: false, relativePath: 'index.md', title: 'SquiRtL' },
  { isNotFound: false, relativePath: 'methods/environment.md', title: 'Environment' },
  { isNotFound: true, relativePath: '404.md', title: '404' },
  { isNotFound: true, relativePath: 'methods/missing.md', title: 'Missing' },
  { isNotFound: false, relativePath: 'methods/reward.md', title: 'Reward' }
]

/**
 * The one section the pages above sit in.
 */
const SECTIONS = [METHODS]

/**
 * The cards the pages above are drawn to, the one the site's pages share
 * written once.
 */
const WRITTEN = ['cards/site.png', 'cards/methods/environment.png', 'cards/methods/reward.png']

describe('renderCards', () => {
  test('writes the card two pages share once', async ({ checkout }) => {
    const { root: folder } = checkout()
    const written          = await renderCards(FACTS, import.meta.url, folder, PAGES, SECTIONS)
    const files            = fs.globSync('**/*.png', { cwd: folder }).toSorted()

    expect(written).toEqual(WRITTEN)
    expect(files).toEqual(WRITTEN.toSorted())
  })

  test.for(WRITTEN)('draws %s as a PNG at the card’s size', async (file, { checkout }) => {
    const { root: folder } = checkout()
    await renderCards(FACTS, import.meta.url, folder, PAGES, SECTIONS)
    const png = fs.readFileSync(path.join(folder, file))

    expect(png.subarray(1, 4).toString()).toBe('PNG')
    expect([png.readUInt32BE(16), png.readUInt32BE(20)]).toEqual([CARD.width, CARD.height])
  })

  test('draws a page of no section with the site’s card', async ({ checkout }) => {
    const { root: folder } = checkout()
    const page             = { isNotFound: false, relativePath: 'about.md', title: 'About' }
    await renderCards(FACTS, import.meta.url, folder, [PAGES[0]!, page])

    const read = (name: string): Buffer => fs.readFileSync(path.join(folder, 'cards', `${name}.png`))
    expect(read('about')).toEqual(read('site'))
  })
})

describe('Cards', () => {
  test('draws the card of each page added as the build renders it', async ({ checkout }) => {
    const { root: folder } = checkout()
    const cards            = new Cards(FACTS, import.meta.url)
    cards.add(PAGES[0]!)
    cards.add(PAGES[2]!)

    expect(await cards.render(folder)).toEqual(['cards/site.png'])
  })
})
