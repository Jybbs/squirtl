import type { MarkdownRenderer } from 'vitepress'

/**
 * A widget a page carries, beside the page it sits in and the heading
 * of the part of that page it closes, matched against the heading's source, so
 * a command page's title matches as `` `squirtl watch` ``.
 */
export interface Placement {
  heading : string
  name    : string
  page    : string
}

/**
 * The widgets the sections' pages and the Identity page carry, each under the component name the
 * theme registers it by, in the order of their pages and then of their places
 * on each page.
 */
export const WIDGETS: readonly Placement[] = [
  { heading: 'At the Terminal', name: 'CommandsTerminal', page: 'commands/index.md' },
  { heading: '`squirtl fetch`', name: 'CommandsFetch', page: 'commands/fetch.md' },
  { heading: '`squirtl pack`', name: 'CommandsPack', page: 'commands/pack.md' },
  { heading: '`squirtl watch`', name: 'CommandsWatch', page: 'commands/watch.md' },
  { heading: 'The Palette', name: 'IdentityPalette', page: 'identity.md' },
  { heading: 'The Faces', name: 'IdentityFaces', page: 'identity.md' },
  { heading: 'The Logo', name: 'IdentityLogo', page: 'identity.md' },
  { heading: 'The Series Order', name: 'IdentityOrder', page: 'identity.md' },
  { heading: 'The Tagline and Byline', name: 'IdentityTagline', page: 'identity.md' },
  { heading: 'The Results Charts', name: 'IdentityResults', page: 'identity.md' },
  { heading: 'The Discount', name: 'MethodsDiscount', page: 'methods/agents.md' },
  { heading: 'Replay Memory and Rollouts', name: 'MethodsExperience', page: 'methods/agents.md' },
  { heading: 'The Reach of an Update', name: 'MethodsReach', page: 'methods/agents.md' },
  { heading: 'Moving a Window', name: 'MethodsCurriculum', page: 'methods/curriculum.md' },
  { heading: 'A Step', name: 'MethodsStep', page: 'methods/environment.md' },
  { heading: 'The Bytes It Reads', name: 'MethodsMemory', page: 'methods/reward.md' },
  { heading: 'Learning Curves', name: 'ResultsCurves', page: 'results/index.md' },
  { heading: 'Against Random Presses', name: 'ResultsComparison', page: 'results/index.md' }
]

/**
 * Closes each part of a page that `widgets` names on its widget, ahead of the
 * next heading of any level, or else ahead of the first `<details>` the part
 * opens, so a widget stands over the table folded shut beneath it, and the
 * page itself stays bare Markdown that reads whole on GitHub.
 */
export function sectionWidgets(md: MarkdownRenderer, widgets: readonly Placement[] = WIDGETS) {
  md.core.ruler.push('section-widgets', state => {
    const tokens = state.tokens
    const opens  = tokens.flatMap((token, i) => token.type === 'heading_open' ? [i] : [])
    const placed = widgets.filter(({ page }) => page === state.env.relativePath).flatMap(({ heading, name }) => {
      const at = opens.find(i => tokens[i + 1]?.content === heading)
      if (at === undefined) return []
      const end    = opens.find(i => i > at) ?? tokens.length
      const folded = tokens.findIndex((token, i) => i > at && i < end && token.type === 'html_block' && token.content.startsWith('<details'))
      return [{ end: folded === -1 ? end : folded, name }]
    })

    for (const { end, name } of placed.toSorted((left, right) => right.end - left.end)) {
      tokens.splice(end, 0, Object.assign(new state.Token('html_block', '', 0), { content: `<${name} />\n` }))
    }
  })
}
