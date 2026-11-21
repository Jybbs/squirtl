import { createMarkdownRenderer } from 'vitepress'
import { describe, expect, it }   from 'vitest'

import { SINGLES, placed, slugOf }                 from '../../../lib/config/sections.ts'
import { type Placement, WIDGETS, sectionWidgets } from '../../../lib/markdown/widgets.ts'
import { PAGES }                                   from '../../common/pages.ts'

/**
 * A part folding a table shut, the shape a command's page gives its settings.
 */
const FOLD = '<details>\n<summary>The table</summary>\n\nA table.\n\n</details>\n'

/**
 * A command's page in the shape `squirtl write docs` writes one, its title and
 * its help between their markers, its own prose, and its settings between
 * theirs.
 */
const PAGE = [
  '<!-- help -->', '', '# `squirtl watch`', '', 'Plays an episode back.', '', '<!-- /help -->', '',
  'A point of its own.', '', '<!-- settings -->', '', '## Settings', '', 'A table.', '',
  '<!-- /settings -->', ''
].join('\n')

/**
 * The page a case renders, the one each widget a case places closes a part of.
 */
const WATCH = 'commands/watch.md'

/**
 * The widgets a case places, one closing the page's title part and one its
 * settings.
 */
const PLACED: readonly Placement[] = [
  { heading: '`squirtl watch`', name: 'CommandsWatch', page: WATCH },
  { heading: 'Settings', name: 'SettingsTable', page: WATCH }
]

/**
 * Reads the text of each heading the page at `page` under `docs/pages/`
 * carries.
 */
const headingsOf = (page: string): string[] =>
  [...(PAGES[page] ?? '').matchAll(/^#+ (.+)$/gmu)].map(match => match[1]!)

/**
 * Renders `source` as the page at `relativePath`, through a renderer carrying
 * the rule placing `widgets`.
 */
async function rendered(source: string, relativePath: string, widgets = PLACED): Promise<string> {
  const md = await createMarkdownRenderer(
    process.cwd(),
    { config: renderer => sectionWidgets(renderer, widgets) }
  )
  return md.renderAsync(source, { relativePath })
}

describe('sectionWidgets', () => {
  it('closes each part a widget names on it, ahead of the next heading or at the page’s end', async () => {
    const html = await rendered(PAGE, WATCH)

    expect(html).toMatch(/A point of its own\.<\/p>\n<!-- settings -->\n<CommandsWatch \/>\n<h2/u)
    expect(html).toMatch(/<!-- \/settings -->\n<SettingsTable \/>\n$/u)
  })

  it('leaves a page no widget names as it was written', async () => {
    expect(await rendered(PAGE, 'commands/stop.md')).not.toMatch(/<[A-Z]/u)
  })

  it('leaves out a widget whose heading the page lacks', async () => {
    expect(await rendered('# Other\n', WATCH)).not.toMatch(/<[A-Z]/u)
  })

  it('names a heading every widget’s page carries', () => {
    const missing = WIDGETS.filter(({ heading, page }) => !headingsOf(page).includes(heading))

    expect(missing).toStrictEqual([])
  })

  it('places every widget in a section or on a page outside them the site carries', () => {
    const folders = new Set(placed().map(section => section.folder as string))
    const singles = new Set(SINGLES.map(single => `${slugOf(single)}.md`))

    expect(WIDGETS
      .map(({ page }) => page)
      .filter(page => !folders.has(page.split('/')[0]!))
      .filter(page => !singles.has(page))).toStrictEqual([])
  })

  it('closes a part folding a table shut on its widget, ahead of the fold', async () => {
    const html = await rendered('# `squirtl watch`\n\nLead.\n\n' + FOLD, WATCH)

    expect(html).toMatch(/Lead\.<\/p>\n<CommandsWatch \/>\n<details>/u)
  })

  it('closes a page’s last part ahead of the footnotes closing the page', async () => {
    const html = await rendered('# `squirtl watch`\n\nLead.[^source]\n\n[^source]: A source.\n', WATCH)

    expect(html).toMatch(/Lead\.<sup[^\n]*<\/p>\n<CommandsWatch \/>\n<hr class="footnotes-sep">/u)
  })

  it('closes a part with no fold of its own at its next heading, ahead of a later part’s fold', async () => {
    const html = await rendered('# `squirtl watch`\n\nLead.\n\n## Later\n\n' + FOLD, WATCH)

    expect(html).toMatch(/Lead\.<\/p>\n<CommandsWatch \/>\n<h2/u)
  })
})
