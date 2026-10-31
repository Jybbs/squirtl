import type { PageData, Router, TransformContext } from 'vitepress'

/**
 * The words the page at a missing address carries beneath its drawing, its
 * title and its one line on what happened.
 */
export const NOT_FOUND = {
  lead  : 'This address names no page on the site. It may be mistyped, or the page it named may have moved.',
  title : 'Page Not Found'
}

/**
 * Gives every route `router` reaches that leads to no page the title and the
 * description `withNotFound` sets, in place of the `404` and `Not Found` the
 * default theme hands a missing address, which no `transformPageData` reaches.
 */
export function titleNotFound(
  router      : Pick<Router, 'onAfterRouteChange' | 'route'>,
  description : () => string
): void {
  router.onAfterRouteChange = () => {
    router.route.data = withNotFound(router.route.data, description())
  }
}

/**
 * Sets the title the built page at a missing address carries in its `<title>`,
 * which VitePress writes from the default theme's not-found data before any
 * hook runs, to the one `withNotFound` gives the page, and leaves every other
 * page's HTML as it was written.
 */
export function titledHtml(html: string, context: Pick<TransformContext, 'pageData' | 'title'>): string {
  const { pageData, title } = context
  if (!pageData.isNotFound) return html
  const missing = title.replace(pageData.title, NOT_FOUND.title)
  return html.replace(`<title>${title}</title>`, `<title>${missing}</title>`)
}

/**
 * Gives `page` the title and the description the page at a missing address
 * carries where it is that page, `description` being the site's own byline, so
 * a link shared to a missing address still names what the site is, and leaves
 * every other page as it is.
 */
export function withNotFound<Page extends Pick<PageData, 'description' | 'isNotFound' | 'title'>>(
  page        : Page,
  description : string
): Page {
  return page.isNotFound ? { ...page, description, title: NOT_FOUND.title } : page
}
