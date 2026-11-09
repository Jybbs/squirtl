import type { MarkdownRenderer } from 'vitepress'

import { footnotes }      from './footnotes.ts'
import { githubMath }     from './math.ts'
import { frontPage }      from './story.ts'
import { sectionWidgets } from './widgets.ts'

/**
 * Adds the site's own rules to the Markdown renderer VitePress builds, the
 * phones the footnotes render as, the mapping of GitHub's math onto the math
 * plugin, the front page's layout, and the widget closing each part of a
 * section's page that carries one.
 */
export function markdownRules(md: MarkdownRenderer) {
  footnotes(md)
  githubMath(md)
  frontPage(md)
  sectionWidgets(md)
}
