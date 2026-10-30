import type { MarkdownRenderer } from 'vitepress'

import { githubMath } from './math.ts'
import { frontPage }  from './story.ts'

/**
 * Adds the site's own rules to the Markdown renderer VitePress builds, the
 * mapping of GitHub's math onto the math plugin and the front page's layout.
 */
export function markdownRules(md: MarkdownRenderer) {
  githubMath(md)
  frontPage(md)
}
