import type { PageData, SiteConfig, TransformContext } from 'vitepress'

import { Cards }                    from '../cards/render.ts'
import { titledHtml, withNotFound } from '../missing/page.ts'
import { writeCoverage }            from './coverage.ts'
import { pageHead }                 from './head.ts'
import type { ProjectFacts }        from './manifest.ts'
import { withFrontPage }            from './pages.ts'

/**
 * Builds the hooks the build runs on each page and once it ends, reading the
 * checkout holding `metaUrl`: the head each page carries, the page at a missing
 * address titled and described as its own, the front page's layout and hero,
 * the preview card of every page the build rendered, drawn once the build
 * ends, and the coverage figure the suite's last report holds, written beside
 * them.
 */
export function pageHooks(facts: ProjectFacts, metaUrl: string) {
  const cards = new Cards(facts, metaUrl)

  return {
    transformHtml     : (html: string, _: string, context: TransformContext) => titledHtml(html, context),
    transformPageData : (page: PageData) => withFrontPage(page, facts),

    buildEnd: async (site: Pick<SiteConfig, 'outDir'>) => {
      await cards.render(site.outDir)
      writeCoverage(site.outDir, metaUrl)
    },

    transformHead: (context: TransformContext) => {
      const pageData    = withNotFound(context.pageData, facts.description)
      const description = pageData.description || context.description
      cards.add(pageData)
      return pageHead({ ...context, description, pageData }, facts)
    }
  }
}
