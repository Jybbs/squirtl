import fs from 'node:fs'

import type { PageData, TransformContext } from 'vitepress'
import { describe, expect }                from 'vitest'

import { pageHead }  from '../../../lib/config/head.ts'
import { pageHooks } from '../../../lib/config/hooks.ts'
import { test }      from '../../common/checkout.ts'
import { FACTS }     from '../../common/facts.ts'

/**
 * The front page as the build renders it.
 */
const FRONT = {
  frontmatter  : {},
  isNotFound   : false,
  relativePath : 'index.md',
  title        : 'SquiRtL'
} as unknown as PageData

/**
 * The page at a missing address as the default theme hands it to the build.
 */
const MISSING = { description: 'Not Found', isNotFound: true, relativePath: '404.md', title: '404' } as PageData

/**
 * The context the build hands the front page's head, the fields the head reads.
 */
const CONTEXT = {
  description : FACTS.description,
  pageData    : FRONT,
  siteData    : { lang: 'en-US' }
} as TransformContext

describe('pageHooks', () => {
  test('writes each page’s head and gives the front page its hero', () => {
    const hooks = pageHooks(FACTS, import.meta.url)

    expect(hooks.transformHead(CONTEXT)).toStrictEqual(pageHead(CONTEXT, FACTS))
    expect(hooks.transformPageData(FRONT)?.frontmatter?.['layout']).toBe('home')
  })

  test('draws the card of each page whose head it wrote once the build ends', async ({ checkout }) => {
    const { root: outDir } = checkout()
    const hooks            = pageHooks(FACTS, import.meta.url)
    hooks.transformHead(CONTEXT)
    await hooks.buildEnd({ outDir })

    expect(fs.globSync('**/*.png', { cwd: outDir })).toStrictEqual(['cards/site.png'])
  })

  test('titles and describes the page at a missing address as its own in its head and its built title', () => {
    const hooks   = pageHooks(FACTS, import.meta.url)
    const context = { ...CONTEXT, description: 'Not Found', pageData: MISSING, title: '404 | SquiRtL' }
    const own     = { ...MISSING, description: FACTS.description, title: 'Page Not Found' }

    expect(hooks.transformHead(context))
      .toStrictEqual(pageHead({ ...context, description: FACTS.description, pageData: own }, FACTS))
    expect(hooks.transformHtml('<title>404 | SquiRtL</title>', '404.html', context))
      .toBe('<title>Page Not Found | SquiRtL</title>')
  })
})
