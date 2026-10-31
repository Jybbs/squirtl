import { describe, expect, it } from 'vitest'

import * as page from '../../../lib/missing/page.ts'

/**
 * The data the default theme hands the page at a missing address.
 */
const MISSING = { description: 'Not Found', isNotFound: true, title: '404' }

/**
 * The HTML VitePress writes for that page, as far as its title reads it.
 */
const HTML = '<head><title>404 | SquiRtL</title><meta name="description" content="Plays."></head>'

describe('withNotFound', () => {
  it('titles the page at a missing address as its own and describes it by the byline given', () => {
    expect(page.withNotFound(MISSING, 'Plays.'))
      .toStrictEqual({ description: 'Plays.', isNotFound: true, title: 'Page Not Found' })
  })

  it('leaves every other page as it is', () => {
    const found = { description: '', isNotFound: false, title: 'Agent' }

    expect(page.withNotFound(found, 'Plays.')).toBe(found)
  })
})

describe('titledHtml', () => {
  it('writes the page’s own title in place of 404 inside the title VitePress built', () => {
    expect(page.titledHtml(HTML, { pageData: MISSING as never, title: '404 | SquiRtL' }))
      .toBe(HTML.replace('404 | SquiRtL', 'Page Not Found | SquiRtL'))
  })

  it('leaves every other page’s HTML as it was written', () => {
    const pageData = { ...MISSING, isNotFound: false } as never

    expect(page.titledHtml(HTML, { pageData, title: '404 | SquiRtL' })).toBe(HTML)
  })
})

describe('titleNotFound', () => {
  it('gives the route the page’s own title and the byline after each change of route', () => {
    const router = { onAfterRouteChange: undefined as (() => void) | undefined, route: { data: MISSING } }

    page.titleNotFound(router as never, () => 'Plays.')
    router.onAfterRouteChange!()

    expect(router.route.data).toStrictEqual(page.withNotFound(MISSING, 'Plays.'))
  })
})
