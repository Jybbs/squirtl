// @vitest-environment happy-dom
import { describe, expect, it, vi } from 'vitest'
import { createApp }                from 'vue'

vi.mock('vitepress/theme-without-fonts', () => ({ default: {} }))

const { default: theme }        = await import('../../theme/index.ts')
const { default: DefaultTheme } = await import('vitepress/theme-without-fonts')
const { STORY }                 = await import('../../lib/markdown/story.ts')

describe('the theme', () => {
  it('extends the default theme and registers a widget for each chapter of the story', () => {
    const app = createApp({})

    theme.enhanceApp({ app } as never)

    expect(theme.extends).toBe(DefaultTheme)
    expect(STORY.filter(chapter => !app.component(chapter.name))).toStrictEqual([])
  })
})
