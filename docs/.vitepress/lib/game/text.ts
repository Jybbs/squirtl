import FONT                            from '../art/font.json' with { type: 'json' }
import { type Grid, type Run, runsOf } from '../drawing/sprites.ts'
import { type Painter, paintRuns }     from './screen.ts'

/**
 * A character the game's font draws, a letter or one of the text box's border
 * tiles.
 */
type Glyph = keyof typeof FONT

/**
 * A text box in the screen's eight-pixel tiles, the column and the row of its
 * top left tile and the tiles it spans across and down, its border included.
 */
export interface TextBox {
  column  : number
  columns : number
  row     : number
  rows    : number
}

/**
 * The pixels on each side of one of the Game Boy's tiles, the unit its text and
 * its text boxes are laid out in.
 */
export const TILE = 8

/**
 * The runs each glyph of the game's font draws, split once as the module loads
 * from the rows pret/pokered's `gfx/font/font.png` and the text box's border
 * tiles in `gfx/font/font_extra.png` hold, every pixel set in the darkest shade.
 */
const glyphRuns = new Map(Object.entries(FONT).map(([glyph, rows]) => [glyph, runsOf(gridOf(rows))]))

/**
 * Reads a glyph's eight rows of eight pixels, written as two hex digits a row,
 * as a grid of the darkest shade over the lightest.
 */
function gridOf(rows: string): Grid {
  return Array.from({ length: TILE }, (_, row) => {
    const bits = Number.parseInt(rows.slice(2 * row, 2 * row + 2), 16)
    return bits.toString(2).padStart(TILE, '0').replaceAll('1', '3')
  })
}

/**
 * Reads the runs `glyph` draws.
 */
function runsAt(glyph: Glyph): readonly Run[] {
  return glyphRuns.get(glyph)!
}

/**
 * Draws `box` as the game's `TextBoxBorder` draws one, its inside filled in the
 * lightest of `shades` and its corner and edge tiles drawn in the darkest.
 */
export function paintBox(context: Painter, box: TextBox, shades: readonly string[]): void {
  const { column, columns, row, rows } = box
  const left                           = column * TILE
  const top                            = row * TILE
  const right                          = (column + columns - 1) * TILE
  const bottom                         = (row + rows - 1) * TILE
  context.fillStyle                    = shades[0]!
  context.fillRect(left, top, columns * TILE, rows * TILE)
  const tiles: [Glyph, number, number][] = [
    ['┌', left, top], ['┐', right, top], ['└', left, bottom], ['┘', right, bottom]
  ]
  for (let x = left + TILE; x < right; x += TILE) tiles.push(['─', x, top], ['─', x, bottom])
  for (let y = top + TILE; y < bottom; y += TILE) tiles.push(['│', left, y], ['│', right, y])
  for (const [glyph, x, y] of tiles) paintRuns(context, runsAt(glyph), x, y, shades)
}

/**
 * Draws `text` in the game's font from its top left at `x` and `y`, one tile to
 * a character, in the darkest of `shades` over the lightest.
 */
export function paintText(
  context : Painter,
  text    : string,
  x       : number,
  y       : number,
  shades  : readonly string[]
): void {
  for (const [at, glyph] of [...text].entries()) {
    paintRuns(context, runsAt(glyph as Glyph), x + at * TILE, y, shades)
  }
}
