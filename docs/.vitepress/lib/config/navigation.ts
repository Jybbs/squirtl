import fs   from 'node:fs'
import path from 'node:path'

import { createMarkdownRenderer, disposeMdItInstance } from 'vitepress'
import type { DefaultTheme, MarkdownRenderer }        from 'vitepress'

import type { Edition }                   from '../cards/cards.ts'
import { SECTIONS, type Section, placed } from './sections.ts'

/**
 * The theme's configuration as the site sets it, the default theme's beside the
 * version and the host a card's edition plate names, which a component drawing
 * a card in a page reads.
 */
export interface SiteTheme extends DefaultTheme.Config {
  edition: Edition
}

/**
 * Reads the first level-1 heading of the Markdown file at `file`, which names
 * the page in the sidebar as it names it for VitePress's own title.
 */
function headingOf(file: string): string {
  const heading = /^# (.+)$/mu.exec(fs.readFileSync(file, 'utf8'))?.[1]
  if (!heading) throw new Error(`${file} opens on no level-1 heading`)
  return heading
}

/**
 * Renders the inline Markdown of `heading` as the page renders it, for the
 * default theme to set as an entry's label, and returns it beside the heading's
 * plain text, which the entries sort by.
 */
function labelOf(md: MarkdownRenderer, heading: string): { html: string, text: string } {
  const tokens = md.parseInline(heading, {})[0]?.children ?? []
  return {
    html : md.renderer.renderInline(tokens, md.options, {}),
    text : tokens.map(token => token.content).join('')
  }
}

/**
 * Lists each section in the navigation bar, linking its overview.
 */
export function buildNav(sections: readonly Section[] = SECTIONS): DefaultTheme.NavItemWithLink[] {
  return placed(sections).map(section => ({
    activeMatch : `^/${section.folder}/`,
    link        : `/${section.folder}/`,
    text        : section.name
  }))
}

/**
 * Lists the pages of each section under `pages` in the sidebar its folder
 * shows, each labeled with its heading as the page renders it, the overview
 * first and every other page after it in the alphabetical order of its
 * heading's text.
 */
export async function buildSidebar(
  pages    : string,
  sections : readonly Section[] = SECTIONS
): Promise<DefaultTheme.SidebarMulti> {
  const md = await createMarkdownRenderer(pages)
  try {
    return Object.fromEntries(placed(sections).map(section => {
      const folder  = path.join(pages, section.folder)
      const entries = fs.globSync('*.md', { cwd: folder, exclude: ['index.md'] })
        .map(file => ({
          label : labelOf(md, headingOf(path.join(folder, file))),
          page  : path.basename(file, '.md')
        }))
        .toSorted((left, right) => left.label.text.localeCompare(right.label.text))
        .map(({ label, page }) => ({ link: `/${section.folder}/${page}`, text: label.html }))

      return [`/${section.folder}/`, [{ items: entries, link: `/${section.folder}/`, text: section.name }]]
    }))
  } finally {
    // Releases the renderer, since VitePress hands the first one built to every
    // later caller, and the site's own would otherwise render without its rules.
    disposeMdItInstance()
  }
}
