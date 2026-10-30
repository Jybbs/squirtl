import type { MarkdownRenderer } from 'vitepress'

import { isFrontPage } from '../config/pages.ts'

/**
 * A widget the front page tells the project's story through, beside the heading
 * of the section it stands in.
 */
export interface Chapter {
  heading : string
  name    : string
}

/**
 * The widgets the front page carries beneath its hero, in the order its
 * sections tell the story, each under the component name the theme registers it
 * by.
 */
export const STORY: readonly Chapter[] = [
  { heading: 'The Reward', name: 'StoryReward' },
  { heading: 'What the Network Sees', name: 'StorySees' },
  { heading: 'Learning in the Page', name: 'StoryLearning' },
  { heading: 'Against Random Presses', name: 'StoryRace' }
]

/**
 * Lays out the front page on the site, where its first heading and the tagline
 * beneath it render as the hero rather than as content, and each section
 * `story` names becomes a numbered chapter holding its prose above its widget,
 * so the page itself stays bare Markdown that reads whole on GitHub.
 */
export function frontPage(md: MarkdownRenderer, story: readonly Chapter[] = STORY) {
  md.core.ruler.push('front-page', state => {
    if (!isFrontPage(state.env.relativePath)) return
    const tokens = state.tokens
    const title  = tokens.findIndex(token => token.type === 'heading_open' && token.tag === 'h1')
    // Counts three tokens, open, inline, and close, for the heading and for the tagline's paragraph.
    if (title !== -1) tokens.splice(title, /^\*[^*].*\*$/u.test(tokens[title + 4]?.content ?? '') ? 6 : 3)

    const opens    = (token: (typeof tokens)[number]) => token.type === 'heading_open' && token.tag === 'h2'
    const starts   = tokens.flatMap((token, i) => opens(token) ? [i] : [])
    const chapters = story.flatMap(({ heading, name }) => {
      const at = starts.find(i => tokens[i + 1]?.content === heading)
      return at === undefined ? [] : [{ at, end: starts.find(i => i > at) ?? tokens.length, name }]
    })
    const block = (content: string) => Object.assign(new state.Token('html_block', '', 0), { content })

    for (const { at, end, name } of chapters.toSorted((left, right) => right.at - left.at)) {
      tokens.splice(end, 0, block(`<${name} />\n`), block('</section>\n'))
      tokens.splice(at, 0, block('<section class="story">\n'))
    }
  })
}
