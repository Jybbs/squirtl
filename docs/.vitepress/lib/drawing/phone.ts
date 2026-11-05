/**
 * The drawings a citation renders, each a string of markup written into a page
 * at build time and hidden from the accessibility tree: the Rotom Phone upright
 * or as one slab across a run of numerals, the larger phone opening a
 * definition and holding the list, and the arrow each way back draws.
 */

const CELL      = 11
const CELL_WIDE = 18

/**
 * Writes one drawing from its size and its shapes.
 */
function svg(width: number, height: number, body: string, name = ''): string {
  return `<svg class="${name}" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" aria-hidden="true">${body}</svg>`
}

/**
 * Writes the ringed lens, its highlight drawn where `shine` gives a radius.
 */
function lens(x: number, y: number, ring: number, glass: number, shine = 0): string {
  const highlight = shine
    ? `<circle class="footnote-shine" cx="${x - glass * 0.35}" cy="${y - glass * 0.35}" r="${shine}"/>`
    : ''
  return `<circle class="footnote-ring" cx="${x}" cy="${y}" r="${ring}"/><circle class="footnote-lens" cx="${x}" cy="${y}" r="${glass}"/>${highlight}`
}

/**
 * Writes the lightning-bolt antenna, its left edge at `x`.
 */
function bolt(x: number): string {
  return `<path class="footnote-bolt" d="M${x + 2} 6 ${x + 3} 3.5 ${x + 1} 3.5 ${x + 6} 0 ${x + 5} 2.5 ${x + 7} 2.5 ${x + 4} 6Z"/>`
}

/**
 * Writes the spike beneath the phone, its left edge at `x`.
 */
function spike(x: number): string {
  return `<path class="footnote-shell" d="M${x + 1.5} 21.5H${x + 5.5}L${x + 3} 25Z"/>`
}

/**
 * Writes a number on the glass in the code face.
 */
function numeral(number: number): string {
  return `<span class="footnote-numeral">${number}</span>`
}

/**
 * Writes a number in its cell on the phone's glass.
 */
function screen(number: number): string {
  return `<span class="footnote-screen">${numeral(number)}</span>`
}

/**
 * The lens every marker holds on its phone's corner, drawn over the numeral.
 */
const CORNER = svg(8, 8, `<circle class="footnote-shell" cx="4" cy="4" r="4"/>${lens(4, 4, 3, 2)}`, 'footnote-art-corner')

/**
 * The arrow a way back draws, a hook turning back.
 */
export const BACK_ARROW = svg(16, 16, '<path d="M6.500 2.500 2 7l4.500 4.500M2.800 7H10a4 4 0 0 1 4 4v2.500" fill="none" stroke="currentColor" stroke-linecap="square" stroke-width="2.200"/>')

/**
 * The drawings around the list: the camera on the phone's corner, the bolt
 * above it, and the spike beneath it.
 */
export const PHONE_ART = [
  `<span class="footnote-phone-camera">${svg(68, 34, `<rect class="footnote-shell" width="68" height="34" rx="17"/>${lens(17, 17, 13, 10, 3)}<circle class="footnote-ring" cx="49" cy="17" r="10"/><circle class="footnote-camera-two" cx="49" cy="17" r="6.500"/>`)}</span>`,
  `<span class="footnote-phone-bolt">${svg(64, 46, '<path class="footnote-bolt" d="M20 46 27 26 14 26 48 0 39 19 54 19 32 46Z"/>')}</span>`,
  `<span class="footnote-phone-foot">${svg(40, 26, '<path class="footnote-shell" d="M0 0H40L30 10H25L20 26 15 10H10Z"/>')}</span>`
].join('')

/**
 * Writes the larger phone opening a definition, holding its number.
 */
export function opener(number: number): string {
  const phone = svg(36, 54, `<rect class="footnote-shell" x="4" y="10" width="30" height="36" rx="6"/><path class="footnote-bolt" d="M18 12 20 6 15 6 26 0 23.500 4.500 28 4.500 22 12Z"/><path class="footnote-shell" d="M13 45H25L19 54Z"/><rect class="footnote-pane" x="7.500" y="13.500" width="23" height="29" rx="3"/><circle class="footnote-shell" cx="9" cy="13" r="8.500"/>${lens(9, 13, 6.5, 4.8, 1.4)}`)
  return `<span class="footnote-opener">${phone}${numeral(number)}</span>`
}

/**
 * Writes a lone marker, the phone upright with its number on the glass.
 */
export function lone(number: number): string {
  const phone = svg(16, 25, `<rect class="footnote-shell" x="3" y="5" width="13" height="17" rx="3"/>${bolt(6)}${spike(6)}`, 'footnote-art-phone')
  return `<span class="footnote-tile footnote-lead footnote-alone">${phone}${screen(number)}${CORNER}</span>`
}

/**
 * Writes the slab of a run: one phone across every numeral, its glass parted
 * into one pane per numeral with the shell showing through as a bar between
 * two, and the bolt and the spike on its center axis.
 */
function slab(numbers: readonly number[]): string {
  const widths = numbers.map(number => (number > 9 ? CELL_WIDE : CELL))
  const width  = 4 + widths.reduce((sum, wide) => sum + wide, 0) + widths.length - 1
  let   left   = 5
  const panes  = widths.map(wide => {
    const pane = `<rect class="footnote-pane" x="${left}" y="7" width="${wide}" height="13" rx="1"/>`
    left += wide + 1
    return pane
  })
  const axis = width / 2 - 0.5
  return svg(width + 3, 25, `<rect class="footnote-shell" x="3" y="5" width="${width}" height="17" rx="3"/>${panes.join('')}${bolt(axis)}${spike(axis)}`, 'footnote-art-phone')
}

/**
 * Writes one numeral's cell in a run, the first holding the slab behind every
 * later link and the lens over it, so the bar between two numerals takes no
 * pointer event and no drawing joins any link's name.
 */
export function cell(number: number, numbers: readonly number[], position: number): string {
  const first   = position === 0
  const last    = position === numbers.length - 1
  const classes = [
    'footnote-tile footnote-cell',
    first ? 'footnote-first' : '',
    last ? 'footnote-last' : '',
    number > 9 ? 'footnote-wide' : ''
  ].filter(Boolean).join(' ')
  return `<span class="${classes}">${first ? slab(numbers) : ''}${screen(number)}${first ? CORNER : ''}</span>`
}
