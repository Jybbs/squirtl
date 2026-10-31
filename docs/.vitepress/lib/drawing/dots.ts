import { IDENTITY } from '../identity/identity.ts'

/**
 * One cell of the display face a character lights, as its column from the
 * character's left and its row up from the baseline.
 */
export type Cell = readonly [column: number, row: number]

/**
 * A run of text laid out in the display face's cells, each character at the
 * column it starts on.
 */
export interface Laid {
  letters : readonly Letter[]
  width   : number
}

/**
 * One character of laid-out text.
 */
interface Letter {
  cells : readonly Cell[]
  char  : string
  x     : number
}

/**
 * How `dotText` sets text, the side of one cell, its baseline's left end, and
 * each dot's fill, given whole or chosen per dot from its column, its row, and
 * its character's place in the text.
 */
export interface Setting {
  cell : number
  fill : string | ((column: number, row: number, letter: number) => string)
  x    : number
  y    : number
}

/**
 * The radius of a dot as a share of its cell, which overlaps neighboring dots
 * so they fuse into the face's strokes.
 */
const RADIUS = 0.6

/**
 * Reads the glyph the identity declares for `char`, or the one for `?` where it
 * declares none.
 */
const glyphOf = (char: string) =>
  (IDENTITY.glyphs as Record<string, { advance: number, cells: string }>)[char] ?? IDENTITY.glyphs['?']

/**
 * Reads the cells a character spans, the space after it included.
 */
export const advanceOf = (char: string): number => glyphOf(char).advance

/**
 * Reads the cells `char` lights out of the identity's glyph, where each pair of
 * hex digits holds a column and a row raised by five.
 */
export function cellsOf(char: string): Cell[] {
  return Array.from(
    glyphOf(char).cells.matchAll(/(.)(.)/gu),
    ([, column, row]) => [Number.parseInt(column!, 16) - 5, Number.parseInt(row!, 16) - 5] as const
  )
}

/**
 * Draws `text` in the display face as SVG circles, one per lit cell.
 */
export function dotText(text: string, setting: Setting): string {
  const { cell, fill, x, y } = setting
  return layout(text).letters
    .flatMap((letter, n) => letter.cells.map(([column, row]) => {
      const left  = letter.x + column
      const paint = typeof fill === 'function' ? fill(left, row, n) : fill
      return `<circle cx="${(x + (left + 0.5) * cell).toFixed(1)}" `
           + `cy="${(y - (row + 0.5) * cell).toFixed(1)}" r="${(cell * RADIUS).toFixed(1)}" fill="${paint}"/>`
    }))
    .join('')
}

/**
 * Lays `text` out from column 0, each character starting where the one before
 * it advances to.
 */
export function layout(text: string): Laid {
  const letters: Letter[] = []
  let x                   = 0
  for (const char of text) {
    letters.push({ cells: cellsOf(char), char, x })
    x += advanceOf(char)
  }
  return { letters, width: x - 1 }
}
