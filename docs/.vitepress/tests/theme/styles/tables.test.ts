// @vitest-environment happy-dom
import fs   from 'node:fs'
import path from 'node:path'

import { createMarkdownRenderer } from 'vitepress'
import { describe, expect, it }   from 'vitest'

/**
 * The folder holding the site's pages.
 */
const PAGES = path.join(import.meta.dirname, '../../../../pages')

/**
 * The sheet the theme styles a page's tables with.
 */
const SHEET = fs.readFileSync(path.join(import.meta.dirname, '../../../theme/styles/tables.css'), 'utf8')

/**
 * Reads the page at `name`, a path under the site's pages.
 */
const page = (name: string): string => fs.readFileSync(path.join(PAGES, name), 'utf8')

/**
 * Lists the `white-space` value computed for each element `selector` matches.
 */
const spaces = (selector: string): string[] =>
  [...document.querySelectorAll(selector)].map(element => getComputedStyle(element).whiteSpace)

/**
 * Renders the page at `name` inside the default theme's content column, styled
 * by `tables.css`, and reports how each code span in a table cell wraps, keyed
 * by whether it sits in the cell alone or inside the cell's prose.
 */
async function wrapping(name: string): Promise<{ alone: string[]; prose: string[] }> {
  const md = await createMarkdownRenderer(process.cwd())

  document.body.innerHTML = `<style>${SHEET}</style><div class="vp-doc">${await md.renderAsync(page(name))}</div>`

  return { alone: spaces('td > code'), prose: spaces('td > em > code') }
}

describe('tables.css', () => {
  const tabled = fs.globSync('**/*.md', { cwd: PAGES }).filter(name => page(name).includes('\n|---'))

  it('finds the table on a command’s page', () => {
    expect(tabled).toContain('commands/train.md')
  })

  it.for(tabled)('keeps each code span set alone in a cell of %s on one line while the cell’s prose wraps', async name => {
    const { alone, prose } = await wrapping(name)

    expect(alone.length).toBeGreaterThan(0)
    expect([...new Set(alone)]).toStrictEqual(['nowrap'])
    expect(prose).not.toContain('nowrap')
  })
})
