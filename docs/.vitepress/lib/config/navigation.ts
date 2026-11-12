import fs   from 'node:fs'
import path from 'node:path'

import type { DefaultTheme } from 'vitepress'

import type { Edition }                   from '../cards/cards.ts'
import type { ProjectFacts }              from './manifest.ts'
import { SECTIONS, SINGLES, type Section, type Single, placed, slugOf } from './sections.ts'

/**
 * The facts about the project a component sets out in a page, the byline, the
 * coverage gate, the host, the keywords, the least Python, and the
 * repository's address.
 */
export type Project = Pick<ProjectFacts, 'description' | 'gate' | 'host' | 'keywords' | 'python' | 'repository'>

/**
 * The theme's configuration as the site sets it, the default theme's beside the
 * version and the host a card's edition plate names, which a component drawing
 * a card in a page reads, and the facts about the project a page sets out.
 */
export interface SiteTheme extends DefaultTheme.Config {
  edition : Edition
  project : Project
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
 * Lists each section in the navigation bar, linking its overview, and after
 * them each of `singles`, linking its page.
 */
export function buildNav(
  sections : readonly Section[] = SECTIONS,
  singles  : readonly Single[] = SINGLES
): DefaultTheme.NavItemWithLink[] {
  return [
    ...placed(sections).map(section => ({
      activeMatch : `^/${section.folder}/`,
      link        : `/${section.folder}/`,
      text        : section.name
    })),
    ...singles.map(single => ({
      activeMatch : `^/${slugOf(single)}$`,
      link        : `/${slugOf(single)}`,
      text        : single.name
    }))
  ]
}

/**
 * Lists the pages of each section under `pages` in the sidebar its folder
 * shows, the overview first and every other page after it in the alphabetical
 * order of its heading.
 */
export function buildSidebar(
  pages    : string,
  sections : readonly Section[] = SECTIONS
): DefaultTheme.SidebarMulti {
  return Object.fromEntries(placed(sections).map(section => {
    const folder  = path.join(pages, section.folder)
    const entries = fs.globSync('*.md', { cwd: folder, exclude: ['index.md'] })
      .map(file => ({
        link : `/${section.folder}/${path.basename(file, '.md')}`,
        text : headingOf(path.join(folder, file))
      }))
      .toSorted((left, right) => left.text.localeCompare(right.text))

    return [`/${section.folder}/`, [{ items: entries, link: `/${section.folder}/`, text: section.name }]]
  }))
}
