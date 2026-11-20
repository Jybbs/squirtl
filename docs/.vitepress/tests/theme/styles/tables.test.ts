import { Window }                         from 'happy-dom'
import { createMarkdownRenderer }         from 'vitepress'
import { afterAll, describe, expect, it } from 'vitest'

import { markdownRules } from '../../../lib/markdown/rules.ts'
import tablesSheet       from '../../../theme/styles/tables.css?raw'
import { PAGES }         from '../../common/pages.ts'

/**
 * A page under `docs/pages/`, its path there beside its text.
 */
interface Page {
  name : string
  text : string
}

/**
 * The HTML each page renders to, kept as each case first renders it.
 */
const RENDERED = new Map<string, Promise<string>>()
/**
 * The window each case renders a page into, built in Node's environment because
 * Vitest's `--changed` reads no `.md?raw` import of a file running under the
 * `happy-dom` environment, where Vite rewrites it to `.md?import&raw`.
 */
const dom = new Window()

/**
 * Lists the value of `property` computed for each element `selector` matches.
 */
const computed = (selector: string, property: string): string[] =>
  [...dom.document.querySelectorAll(selector)]
    .map(element => dom.getComputedStyle(element).getPropertyValue(property))

/**
 * Sets the document to the page at `name` as `styled` reads it, each page
 * rendered once for every case reading it.
 */
async function render({ name, text }: Page) {
  dom.document.body.innerHTML = await RENDERED.getOrInsertComputed(name, () => styled(name, text))
}

/**
 * Reads the HTML of `text`, the page at `name`, through the site's Markdown
 * rules, inside the default theme's content column and styled by `tables.css`.
 */
async function styled(name: string, text: string): Promise<string> {
  const md   = await createMarkdownRenderer(process.cwd(), { config: markdownRules, math: true })
  const body = await md.renderAsync(text, { relativePath: name })

  return `<style>${tablesSheet}</style><div class="vp-doc">${body}</div>`
}

afterAll(() => dom.happyDOM.close())

describe('tables.css', () => {
  const tabled = Object.entries(PAGES)
    .filter(([, text]) => text.includes('\n|---'))
    .map(([name, text]) => ({ name, text }))

  it('finds the table on a command’s page', () => {
    expect(tabled.map(({ name }) => name)).toContain('commands/train.md')
  })

  it.for(tabled)('lays each table of $name across the column inside a block scrolling sideways', async page => {
    await render(page)

    const tables = dom.document.querySelectorAll('table')

    expect(tables.length).toBeGreaterThan(0)
    expect([...tables].filter(table => !table.parentElement?.matches('.table-scroll'))).toStrictEqual([])
    expect([...new Set(computed('.table-scroll', 'overflow-x'))]).toStrictEqual(['auto'])
    expect([...new Set(computed('table', 'display'))]).toStrictEqual(['table'])
    expect([...new Set(computed('table', 'width'))]).toStrictEqual(['100%'])
  })

  it.for(tabled)('keeps each code span set alone in a cell of $name on one line while the cell’s prose wraps', async page => {
    await render(page)

    const alone = computed('td > code', 'white-space')

    expect(alone.length).toBeGreaterThan(0)
    expect([...new Set(alone)]).toStrictEqual(['nowrap'])
    expect(computed('td > em > code', 'white-space')).not.toContain('nowrap')
  })
})
