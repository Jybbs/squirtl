import { createMarkdownRenderer } from 'vitepress'
import { describe, expect, it }   from 'vitest'

import { githubMath } from '../../../lib/markdown/math.ts'

/**
 * Renders `source` through a renderer built the way the site's configuration
 * builds it, with the math plugin and the mapping of GitHub's forms onto it.
 */
async function rendered(source: string): Promise<string> {
  const md = await createMarkdownRenderer(process.cwd(), { config: githubMath, math: true })
  return md.renderAsync(source)
}

/**
 * Replaces the `mjx-` id `markdown-it-mathjax3` draws at random for each math
 * span with one fixed name, so two renders of the same math compare equal.
 */
function withoutIds(html: string): string {
  return html.replaceAll(/(?<=id="|#)mjx-[\da-f]+/gu, 'mjx-id')
}

describe('githubMath', () => {
  it.each([
    ['the inline form', 'Each step decays by $`\\gamma`$ before the next.'],
    ['the block form', '```math\n\\epsilon_t = 1 - t / T\n```']
  ])('renders %s as math rather than as code', async (_, source) => {
    const html = await rendered(source)

    expect(html).toContain('<mjx-container')
    expect(html).not.toContain('<code')
  })

  it('renders the inline form as the plugin renders the same math between bare dollars', async () => {
    const [inline, dollars] = await Promise.all([
      rendered('Decays by $`\\gamma`$.'),
      rendered('Decays by $\\gamma$.')
    ])

    expect(withoutIds(inline)).toBe(withoutIds(dollars))
  })

  it('leaves a code span with no dollar beside it as code', async () => {
    expect(await rendered('The `gamma` key.')).toContain('<code>gamma</code>')
  })
})
