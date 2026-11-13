import type { MarkdownRenderer } from 'vitepress'

/**
 * Sets each table in a block of its own, `div.table-scroll`, which scrolls
 * sideways where the table runs wider than the column, so `tables.css` can lay
 * the table itself out across the column in place of the default theme's
 * content-sized block.
 */
export function scrollingTables(md: MarkdownRenderer) {
  md.renderer.rules.table_open  = (tokens, n, options, _, self) =>
    `<div class="table-scroll">${self.renderToken(tokens, n, options)}`
  md.renderer.rules.table_close = (tokens, n, options, _, self) =>
    `${self.renderToken(tokens, n, options)}</div>\n`
}
