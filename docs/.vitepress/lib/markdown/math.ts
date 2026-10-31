import type { MarkdownRenderer } from 'vitepress'

/**
 * Renders the two forms GitHub draws math in through the math plugin VitePress
 * loads, which reads `$…$` inline and `$$…$$` as a block and leaves GitHub's
 * forms as code.
 *
 * A fence whose info string is `math` becomes the plugin's block of display
 * math, and the plugin's own inline rule, which runs ahead of the one reading
 * code spans, takes `` $`…`$ `` as inline math whose content keeps the
 * backticks, which this rule drops.
 */
export function githubMath(md: MarkdownRenderer) {
  md.core.ruler.after('block', 'github-math-block', state => {
    for (const token of state.tokens) {
      if (token.type === 'fence' && token.info.trim() === 'math') token.type = 'math_block'
    }
  })
  md.core.ruler.after('inline', 'github-math-inline', state => {
    for (const token of state.tokens.flatMap(block => block.children ?? [])) {
      if (token.type !== 'math_inline' || !/^`[^`]+`$/u.test(token.content)) continue
      token.content = token.content.slice(1, -1)
    }
  })
}
