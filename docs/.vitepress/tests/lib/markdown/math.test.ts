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
    expect(await rendered('Decays by $`\\gamma`$.')).toBe(await rendered('Decays by $\\gamma$.'))
  })

  it('leaves a code span with no dollar beside it as code', async () => {
    expect(await rendered('The `gamma` key.')).toContain('<code>gamma</code>')
  })
})
