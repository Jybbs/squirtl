// @vitest-environment happy-dom
import { describe, expect, it, vi } from 'vitest'
import { createApp, reactive, ref } from 'vue'

vi.mock('vitepress/theme-without-fonts', () => ({ default: {} }))
vi.mock('vitepress', async original => ({ ...await original<object>(), inBrowser: true }))

const { default: theme }        = await import('../../theme/index.ts')
const { default: DefaultTheme } = await import('vitepress/theme-without-fonts')
const { STORY }                 = await import('../../lib/markdown/story.ts')
const { WIDGETS }               = await import('../../lib/markdown/widgets.ts')

/**
 * Sets the theme up on a fresh app with a router standing on `data`, and reads
 * the router back.
 */
function enhanced(data: object) {
  const app      = createApp({})
  const router   = reactive({ onAfterRouteChange: undefined as (() => void) | undefined, route: { data } })
  const siteData = ref({ description: 'Plays.' })
  theme.enhanceApp({ app, router, siteData } as never)
  return { app, router }
}

describe('the theme', () => {
  it('extends the default theme and registers a widget for each chapter of the story', () => {
    const { app } = enhanced({ isNotFound: false })

    expect(theme.extends).toBe(DefaultTheme)
    expect(STORY.filter(chapter => !app.component(chapter.name))).toStrictEqual([])
  })

  it('registers every widget a section’s page places', () => {
    const { app } = enhanced({ isNotFound: false })

    expect(WIDGETS.filter(placement => !app.component(placement.name)).map(placement => placement.name)).toStrictEqual([])
  })

  it('titles a missing address as its own page and describes it by the site’s byline', () => {
    const { router } = enhanced({ description: 'Not Found', isNotFound: true, title: '404' })

    router.onAfterRouteChange!()

    expect(router.route.data).toStrictEqual({ description: 'Plays.', isNotFound: true, title: 'Page Not Found' })
  })

  it('follows a footnote’s jump in the document', () => {
    enhanced({ isNotFound: false })
    document.body.innerHTML = '<sup class="footnote-ref"><a href="#footnote-a" id="footnote-ref-a"></a></sup><ol><li id="footnote-a"></li></ol>'
    document.querySelector('a')!.addEventListener('click', event => event.preventDefault())
    document.querySelector('a')!.click()

    expect(document.querySelector('#footnote-a')!.classList).toContain('footnote-hit')
  })
})
