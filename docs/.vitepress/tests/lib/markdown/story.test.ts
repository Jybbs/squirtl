import { createMarkdownRenderer } from 'vitepress'
import { describe, expect, it }   from 'vitest'

import { STORY, frontPage } from '../../../lib/markdown/story.ts'

/**
 * A front page in the shape `docs/pages/index.md` keeps, a heading, a tagline,
 * a lead, and two chapters.
 */
const FRONT = [
  '# SquiRtL',
  '',
  '*A tagline.*',
  '',
  'A lead paragraph.',
  '',
  '## The Reward',
  '',
  'What a step pays.',
  '',
  '## Learning in the Page',
  '',
  'How the table learns.'
].join('\n')

/**
 * Renders `source` as the page at `relativePath`, through a renderer carrying
 * the front page's rule.
 */
async function rendered(source: string, relativePath = 'index.md'): Promise<string> {
  const md = await createMarkdownRenderer(process.cwd(), { config: frontPage })
  return md.renderAsync(source, { relativePath })
}

describe('frontPage', () => {
  it('drops the heading and the tagline the hero shows and keeps the lead', async () => {
    const html = await rendered(FRONT)

    expect(html).not.toMatch(/<h1|A tagline/u)
    expect(html).toContain('<p>A lead paragraph.</p>')
  })

  it('sets each chapter its story names in a section closing on its widget', async () => {
    const html = await rendered(FRONT)

    expect(html).toContain('<section class="story">\n<h2')
    expect(html).toMatch(/What a step pays\.<\/p>\n<StoryReward \/>\n<\/section>/u)
    expect(html).toMatch(/How the table learns\.<\/p>\n<StoryLearning \/>\n<\/section>/u)
  })

  it('keeps a heading whose next paragraph is no tagline', async () => {
    expect(await rendered('# SquiRtL\n\nA plain lead.\n')).toContain('<p>A plain lead.</p>')
  })

  it('drops a heading the page carries alone', async () => {
    expect(await rendered('# SquiRtL\n')).toBe('')
  })

  it('leaves every page but the front page as it was written', async () => {
    expect(await rendered(FRONT, 'methods/index.md')).toMatch(/^<h1/u)
  })

  it('tells the story in the order the front page reads it', () => {
    expect(STORY.map(chapter => chapter.name))
      .toStrictEqual(['StoryReward', 'StorySees', 'StoryLearning', 'StoryRace'])
  })
})
