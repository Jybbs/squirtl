import { readFileSync }           from 'node:fs'
import path                       from 'node:path'
import { createMarkdownRenderer } from 'vitepress'
import { describe, expect, it }   from 'vitest'

import { pagesDir }                                from '../../../lib/config/paths.ts'
import { placed }                                  from '../../../lib/config/sections.ts'
import { type Placement, WIDGETS, sectionWidgets } from '../../../lib/markdown/widgets.ts'

/**
 * A command's page in the shape `squirtl write docs` writes one, its title,
 * its help, and its settings.
 */
const PAGE = ['# `squirtl watch`', '', 'Plays an episode back.', '', '## Settings', '', 'A table.'].join('\n')

/**
 * The widgets a case places, one closing the page's title part and one its
 * settings.
 */
const PLACED: readonly Placement[] = [
  { heading: '`squirtl watch`', name: 'CommandsWatch', page: 'commands/watch.md' },
  { heading: 'Settings', name: 'SettingsTable', page: 'commands/watch.md' }
]

/**
 * Reads the text of each heading the page at `page` under `docs/pages/`
 * carries.
 */
const headingsOf = (page: string): string[] =>
  [...readFileSync(path.join(pagesDir(import.meta.url), page), 'utf8').matchAll(/^#+ (.+)$/gmu)].map(match => match[1]!)

/**
 * Renders `source` as the page at `relativePath`, through a renderer carrying
 * the rule placing `widgets`.
 */
async function rendered(source: string, relativePath: string, widgets = PLACED): Promise<string> {
  const md = await createMarkdownRenderer(process.cwd(), { config: renderer => sectionWidgets(renderer, widgets) })
  return md.renderAsync(source, { relativePath })
}

describe('sectionWidgets', () => {
  it('closes each part a widget names on it, ahead of the next heading or at the page’s end', async () => {
    const html = await rendered(PAGE, 'commands/watch.md')

    expect(html).toMatch(/Plays an episode back\.<\/p>\n<CommandsWatch \/>\n<h2/u)
    expect(html).toMatch(/A table\.<\/p>\n<SettingsTable \/>\n$/u)
  })

  it('leaves a page no widget names as it was written', async () => {
    expect(await rendered(PAGE, 'commands/stop.md')).not.toMatch(/<[A-Z]/u)
  })

  it('leaves out a widget whose heading the page lacks', async () => {
    expect(await rendered('# Other\n', 'commands/watch.md')).not.toMatch(/<[A-Z]/u)
  })

  it('names a heading every widget’s page carries', () => {
    const missing = WIDGETS.filter(({ heading, page }) => !headingsOf(page).includes(heading))

    expect(missing).toStrictEqual([])
  })

  it('places every widget in a section the site carries', () => {
    const folders = new Set(placed().map(section => section.folder as string))

    expect(WIDGETS.filter(widget => !folders.has(widget.page.split('/')[0]!))).toStrictEqual([])
  })
})
