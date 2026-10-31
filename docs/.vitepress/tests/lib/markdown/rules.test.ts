import { createMarkdownRenderer } from 'vitepress'
import { describe, expect, it }   from 'vitest'

import { markdownRules } from '../../../lib/markdown/rules.ts'

describe('markdownRules', () => {
  it('renders GitHub’s math and lays out the front page through one renderer', async () => {
    const md   = await createMarkdownRenderer(process.cwd(), { config: markdownRules, math: true })
    const html = await md.renderAsync('# SquiRtL\n\n*A tagline.*\n\n## The Reward\n\nPays $`\\gamma`$.\n', {
      relativePath: 'index.md'
    })

    expect([html.includes('<h1'), html.includes('<section class="story">'), html.includes('<mjx-container')])
      .toStrictEqual([false, true, true])
  })
})
