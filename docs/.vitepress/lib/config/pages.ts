import type { PageData } from 'vitepress'

import { IDENTITY }          from '../identity/identity.ts'
import type { ProjectFacts } from './manifest.ts'

/**
 * Reports whether the page at `relativePath`, a path under `docs/pages/`, is
 * the front page.
 */
export const isFrontPage = (relativePath: string): boolean => relativePath === 'index.md'

/**
 * Gives the front page the default theme's home layout and its hero, naming the
 * project above its tagline and its byline, the description `facts` holds, with
 * a link to the repository, and leaves every other page as it was written.
 */
export function withFrontPage(
  page  : Pick<PageData, 'frontmatter' | 'relativePath'>,
  facts : Pick<ProjectFacts, 'description' | 'repository'>
): Partial<PageData> | undefined {
  if (!isFrontPage(page.relativePath)) return undefined

  return {
    frontmatter: {
      ...page.frontmatter,
      layout : 'home',
      hero   : {
        actions : [{ link: facts.repository, text: 'The Code on GitHub' }],
        name    : IDENTITY.name,
        tagline : facts.description,
        text    : IDENTITY.tagline
      }
    }
  }
}
