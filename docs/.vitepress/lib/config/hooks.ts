import type { PageData, SiteConfig, TransformContext } from 'vitepress'

import { Cards }             from '../cards/render.ts'
import { pageHead }          from './head.ts'
import type { ProjectFacts } from './manifest.ts'
import { withFrontPage }     from './pages.ts'

/**
 * Builds the hooks the build runs on each page and once it ends, reading the
 * checkout holding `metaUrl`: the head each page carries, the front page's
 * layout and hero, and the preview card of every page the build rendered, drawn
 * once the build ends.
 */
export function pageHooks(facts: ProjectFacts, metaUrl: string) {
  const cards = new Cards(facts, metaUrl)

  return {
    transformPageData: (page: PageData) => withFrontPage(page, facts),

    buildEnd: async (site: Pick<SiteConfig, 'outDir'>) => {
      await cards.render(site.outDir)
    },

    transformHead: (context: TransformContext) => {
      cards.add(context.pageData)
      return pageHead(context, facts)
    }
  }
}
