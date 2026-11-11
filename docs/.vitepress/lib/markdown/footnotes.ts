import type { MarkdownRenderer } from 'vitepress'

import { BACK_ARROW, PHONE_ART, cell, lone, opener } from '../drawing/phone.ts'

type RuleState = Parameters<Parameters<MarkdownRenderer['core']['ruler']['push']>[1]>[0]
type Token     = RuleState['tokens'][number]

const SOURCE_KEY  = /^[a-z]+\d{4}[a-z]?$/u
const WORD_JOINER = '⁠'

/**
 * Writes one token of raw markup.
 */
function raw(state: RuleState, type: 'html_block' | 'html_inline', content: string): Token {
  const token = new state.Token(type, '', 0)
  token.content = content
  return token
}

/**
 * Writes the id part naming a footnote's definition and its markers by the
 * key its label holds, escaped for the attribute it lands in, or by its number
 * where it has no label.
 */
function anchored(md: MarkdownRenderer, { meta }: Token): string {
  return `-${md.utils.escapeHtml(meta.label ?? String(meta.id + 1))}`
}

/**
 * Writes the suffix telling a repeated marker of one source from its first.
 */
function repeat({ meta }: Token): string {
  return meta.subId > 0 ? `:${meta.subId}` : ''
}

/**
 * Wraps each run of adjacent markers in an inline that opens and closes on a
 * word joiner, so `white-space: nowrap` holds it on the word it cites, and
 * gives each marker the numbers of its run and its place among them.
 */
function runs(state: RuleState) {
  for (const block of state.tokens) {
    if (block.type !== 'inline' || !block.children) continue

    const children: Token[] = []
    const held: Token[]     = []
    const flush = () => {
      if (held.length === 0) return
      const numbers = held.map(({ meta }) => meta.id + 1)
      held.forEach((token, position) => { token.meta.run = { numbers, position } })
      children.push(
        raw(state, 'html_inline', `<span class="footnote-run">${WORD_JOINER}`),
        ...held.splice(0),
        raw(state, 'html_inline', `${WORD_JOINER}</span>`)
      )
    }

    for (const child of block.children) {
      if (child.type === 'footnote_ref') held.push(child)
      else {
        flush()
        children.push(child)
      }
    }
    flush()
    block.children = children
  }
}

/**
 * Offers a line break after each slash of each address a definition prints, so
 * a line opens on a whole segment of the path.
 */
function breakAddresses(state: RuleState, inline: Token) {
  const children = inline.children ?? []

  for (const [index, child] of children.entries()) {
    if (child.type !== 'link_open' || child.markup !== 'autolink') continue
    const text = children[index + 1]!
    const html = state.md.utils.escapeHtml(text.content).replaceAll(/\/+/gu, '$&<wbr>')
    children[index + 1] = raw(state, 'html_inline', `<span class="footnote-address">${html}</span>`)
  }
}

/**
 * Splits the authors and the year out of the opening text of a definition
 * labeled by a key into a name line ahead of its paragraph, any other footnote
 * standing as written.
 *
 * Returns:
 *   The name line, or nothing where the opening text holds no year.
 */
function nameLine(state: RuleState, inline?: Token): Token[] {
  const first = inline?.children?.[0]
  const match = first?.type === 'text' ? /^(.+?) (\d{4})\. (.*)$/su.exec(first.content) : null

  if (!first || !match) return []

  first.content = match[3]!

  return [raw(state, 'html_block', `<strong class="footnote-name">${state.md.utils.escapeHtml(match[1]!)} ${match[2]}.</strong>`)]
}

/**
 * Rebuilds each definition the plugin closes a page on as the phone's opener,
 * the name line, the paragraph, and the ways back in a slot of their own.
 */
function entries(state: RuleState) {
  const tokens: Token[] = []
  let   keyed  = false
  let   opened: Token[] | null = null

  for (const token of state.tokens) {
    if (token.type === 'footnote_open') {
      tokens.push(token, raw(state, 'html_block', opener(token.meta.id + 1)))
      keyed  = SOURCE_KEY.test(token.meta.label ?? '')
      opened = []
    } else if (token.type === 'footnote_close') {
      const held    = opened!
      const backs   = held.filter(({ type }) => type === 'footnote_anchor')
      const blocks  = held.filter(({ type }) => type !== 'footnote_anchor')
      const inlines = blocks.filter(({ type }) => type === 'inline')

      for (const inline of inlines) breakAddresses(state, inline)

      tokens.push(
        ...(keyed ? nameLine(state, inlines[0]) : []),
        ...blocks,
        raw(state, 'html_block', '<span class="footnote-backs">'),
        ...backs,
        raw(state, 'html_block', '</span>'),
        token
      )
      opened = null
    } else (opened ?? tokens).push(token)
  }

  state.tokens = tokens
}

/**
 * Renders the footnote plugin VitePress bundles as the site's phones: each
 * footnote anchored by its key, every marker of one source numbered alike, each
 * run of markers one slab that never breaks, and the definitions on the glass
 * of a larger phone. Every marker and way back stays a link and the list stays
 * a list, so all of it reads with no script.
 */
export function footnotes(md: MarkdownRenderer) {
  const { rules } = md.renderer

  rules.footnote_anchor_name = (tokens, index) => anchored(md, tokens[index]!)

  rules.footnote_ref = (tokens, index) => {
    const token  = tokens[index]!
    const { id, run } = token.meta
    const number = id + 1
    const mark   = run?.numbers.length > 1 ? cell(number, run.numbers, run.position) : lone(number)
    const name   = anchored(md, token)
    return `<sup class="footnote-ref"><a aria-label="Source ${number}" href="#footnote${name}" id="footnote-ref${name}${repeat(token)}">${mark}</a></sup>`
  }

  rules.footnote_anchor = (tokens, index) => {
    const token = tokens[index]!
    const { id, subId } = token.meta
    return `<a aria-label="Back to citation ${subId + 1} of source ${id + 1}" class="footnote-backref" href="#footnote-ref${anchored(md, token)}${repeat(token)}">${BACK_ARROW}</a>`
  }

  rules.footnote_block_open = () => `<hr class="footnotes-sep"><section class="footnotes footnote-snap"><div class="footnote-phone"><div aria-hidden="true" class="footnote-phone-art">${PHONE_ART}</div><div class="footnote-phone-body"><div class="footnote-phone-glass"><ol class="footnotes-list">\n`

  rules.footnote_block_close = () => '</ol></div></div></div></section>\n'

  md.core.ruler.after('inline', 'footnote-runs', runs)
  md.core.ruler.after('footnoteTail', 'footnote-entries', entries)
}
