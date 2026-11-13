// @vitest-environment happy-dom
import fs   from 'node:fs'
import path from 'node:path'

import { createMarkdownRenderer } from 'vitepress'
import { describe, expect, it }   from 'vitest'

import { pagesDir }      from '../../../lib/config/paths.ts'
import { markdownRules } from '../../../lib/markdown/rules.ts'

/**
 * The folder holding the site's pages.
 */
const PAGES = pagesDir(import.meta.url)

/**
 * The sheet the theme styles a page's tables with.
 */
const SHEET = fs.readFileSync(path.join(import.meta.dirname, '../../../theme/styles/tables.css'), 'utf8')

/**
 * Reads the page at `name`, a path under the site's pages.
 */
const page = (name: string): string => fs.readFileSync(path.join(PAGES, name), 'utf8')

/**
 * Lists the value of `property` computed for each element `selector` matches.
 */
const computed = (selector: string, property: string): string[] =>
  [...document.querySelectorAll(selector)]
    .map(element => getComputedStyle(element).getPropertyValue(property))

/**
 * Renders the page at `name` through the site's Markdown rules inside the
 * default theme's content column, styled by `tables.css`.
 */
async function render(name: string) {
  const md = await createMarkdownRenderer(process.cwd(), { config: markdownRules, math: true })

  document.body.innerHTML = `<style>${SHEET}</style><div class="vp-doc">${await md.renderAsync(page(name), {
    relativePath: name
  })}</div>`
}

describe('tables.css', () => {
  const tabled = fs.globSync('**/*.md', { cwd: PAGES }).filter(name => page(name).includes('\n|---'))

  it('finds the table on a command’s page', () => {
    expect(tabled).toContain('commands/train.md')
  })

  it.for(tabled)('lays each table of %s across the column inside a block scrolling sideways', async name => {
    await render(name)

    const tables = document.querySelectorAll('table')

    expect(tables.length).toBeGreaterThan(0)
    expect([...tables].every(table => table.parentElement?.matches('.table-scroll'))).toBe(true)
    expect([...new Set(computed('.table-scroll', 'overflow-x'))]).toStrictEqual(['auto'])
    expect([...new Set(computed('table', 'display'))]).toStrictEqual(['table'])
    expect([...new Set(computed('table', 'width'))]).toStrictEqual(['100%'])
  })

  it.for(tabled)('keeps each code span set alone in a cell of %s on one line while the cell’s prose wraps', async name => {
    await render(name)

    const alone = computed('td > code', 'white-space')

    expect(alone.length).toBeGreaterThan(0)
    expect([...new Set(alone)]).toStrictEqual(['nowrap'])
    expect(computed('td > em > code', 'white-space')).not.toContain('nowrap')
  })
})
