import { type Laid, layout } from '../drawing/dots.ts'
import type { Placing }      from '../drawing/sprites.ts'
import * as identity         from '../identity/identity.ts'

/**
 * Blue's block in one letter of the mark, the rounded square laid over the
 * two-by-two cells it covers, with the frame he walks in, the frame he stands
 * in between steps, and where his sprite sits inside the square.
 */
export interface Block {
  frame  : number
  letter : string
  mirror : boolean
  radius : number
  side   : number
  sprite : Spot
  stand  : number
  x      : number
  y      : number
}

/**
 * One dot of the mark, as the center it is drawn at and the letter it lights,
 * where a dot of the trail also carries its step along the route and the third
 * of the route that step falls in.
 */
export type Dot = Lit & { kind: 'ahead' | 'ink' } | Lit & { kind: 'trail', step: number, third: number }

/**
 * The route, the block, and the frames of one letter Blue walks through, as the
 * identity declares them.
 */
type LetterWalk = (typeof identity.IDENTITY.logo.letters)[keyof typeof identity.IDENTITY.logo.letters]

/**
 * The center a dot of the mark is drawn at, the character whose cell it lights,
 * and that character's place in the text.
 */
interface Lit {
  index  : number
  letter : string
  x      : number
  y      : number
}

/**
 * The mark laid out as plain data, every dot, every block, the Poké Ball with
 * the place in the text of the letter it ends, the height of the baseline the
 * text sits on, the left edge of each character, and the frame the drawing is
 * viewed through, all in the units the display face's cells are drawn in.
 */
export interface Mark {
  ball     : Spot & { index: number }
  baseline : number
  blocks   : readonly Block[]
  dots     : readonly Dot[]
  lefts    : readonly number[]
  view     : ViewBox
}

/**
 * Where a sprite sits, the left and top of its first pixel and the side of one
 * pixel.
 */
type Spot = Pick<Placing, 'size' | 'x' | 'y'>

/**
 * The theme's color a dot of the mark takes, the scheme's ink for a letter Blue
 * does not walk through, the ground still ahead of him in his letters, or the
 * third of the trail its step falls in, each switching with the scheme.
 */
export type Tone = 'ahead' | 'ink' | 'trail-1' | 'trail-2' | 'trail-3'

/**
 * The frame the mark is viewed through, its left, its top, and its size.
 */
export interface ViewBox {
  height : number
  width  : number
  x      : number
  y      : number
}

/**
 * The rows of cells between the baseline and the mark's zero height, so a cell
 * in row `r` spans from `BASELINE - r - 1` to `BASELINE - r` cells down from
 * zero.
 */
const BASELINE = 7

/**
 * The frames between each of Blue's standing frames and the walking frame
 * facing the same way, his sheet holding the three standing frames first.
 */
const FRAME_OFFSET = 3

/**
 * The cells one side of Blue's block covers, two of the face's cells to the
 * sixteen pixels of an overworld sprite.
 */
const SPAN = 2

/**
 * The letters of the name Blue walks through, in the order the name sets them,
 * which the trail's route visits in that order.
 */
export const logoLetters = [...identity.IDENTITY.name]
  .filter(char => char in identity.IDENTITY.logo.letters)
  .join('')

/**
 * The walk the identity declares for each letter Blue walks through, keyed by
 * the letter.
 */
const walks = identity.IDENTITY.logo.letters as Readonly<Record<string, LetterWalk>>

/**
 * The side of one cell of the display face in the mark's units, which the block
 * covers two of, leaving its outset on every side.
 */
const cell = (identity.IDENTITY.logo.block.size - 2 * identity.IDENTITY.logo.block.outset) / SPAN

/**
 * The cells the trail's route visits, each written as its letter beside its
 * column and row, in the order Blue walks them.
 */
const route = [...logoLetters].flatMap(char =>
  walks[char]!.route.map(([column, row]) => `${char}${column},${row}`))

/**
 * The radius of every dot, half a cell and the block's outset beyond it, so a
 * block's edge meets where the outer dots of the cells it covers end.
 */
export const dotRadius = cell / 2 + identity.IDENTITY.logo.block.outset

/**
 * Lays out Blue's block in each letter of `laid` he walks through, over the
 * two-by-two cells the letter's walk names, with his sprite centered in it.
 */
function blocksOf(laid: Laid): Block[] {
  const { block, sprite } = identity.IDENTITY.logo
  const margin            = (block.size - sprite) / 2

  return laid.letters.flatMap(letter => {
    const walk = walks[letter.char]
    if (!walk) return []
    const [column, row] = walk.block as [number, number]
    const x             = (letter.x + column) * cell - block.outset
    const y             = (BASELINE - row - SPAN) * cell - block.outset
    const pixel         = sprite / identity.IDENTITY.sprites.player.frames[walk.frame]!.length

    return [{
      frame  : walk.frame,
      letter : letter.char,
      mirror : walk.mirror,
      radius : block.radius,
      side   : block.size,
      sprite : { size: pixel, x: x + margin, y: y + margin },
      stand  : walk.frame - FRAME_OFFSET,
      x      : x,
      y      : y
    }]
  })
}

/**
 * Reports whether the cell at `column` and `row` of a letter lies under the
 * block of `walk`, the two-by-two cells whose lower left the walk's `block`
 * names.
 */
function covers(column: number, row: number, walk?: LetterWalk): boolean {
  if (!walk) return false
  const [left, bottom] = walk.block as [number, number]
  return column >= left && column < left + SPAN && row >= bottom && row < bottom + SPAN
}

/**
 * Lays each lit cell of `laid` out as a dot, leaving out the cells under Blue's
 * blocks, a cell the route visits on the trail in the third of the route its
 * step falls in, every other cell of his letters ahead of him, and the cells of
 * every other letter in ink.
 */
function dotsOf(laid: Laid): Dot[] {
  return laid.letters.flatMap((letter, index) => letter.cells
    .filter(([column, row]) => !covers(column, row, walks[letter.char]))
    .map(([column, row]): Dot => {
      const step = route.indexOf(`${letter.char}${column},${row}`)
      const x    = (letter.x + column + 0.5) * cell
      const y    = (BASELINE - row - 0.5) * cell
      if (step < 0) return { index, kind: letter.char in walks ? 'ahead' : 'ink', letter: letter.char, x, y }
      const third = thirdOf(step, route.length - 1)
      return { index, kind: 'trail', letter: letter.char, step, third, x, y }
    }))
}

/**
 * Reads the hexes `scheme` gives the logo, the ground still ahead of Blue in
 * his letters, his block, and the trail's thirds from the oldest to the newest.
 */
export function logoColors(scheme: identity.Scheme): { ahead: string, block: string, thirds: string[] } {
  const { ahead, block, thirds } = identity.IDENTITY.logo[scheme]
  return {
    ahead  : identity.hexOf(ahead as identity.Token),
    block  : identity.hexOf(block as identity.Token),
    thirds : thirds.map(token => identity.hexOf(token as identity.Token))
  }
}

/**
 * Lays `text` out as the mark, each lit cell a dot except the cells under
 * Blue's blocks, with the cells of his letters that the route does not visit
 * left as ground still ahead of him and the last of them holding the Poké Ball,
 * failing where `text` holds none of the letters he walks through.
 */
export function markOf(text: string): Mark {
  const { ball: side, block } = identity.IDENTITY.logo

  const laid    = layout(text)
  const rows    = laid.letters.flatMap(letter => letter.cells.map(([, row]) => row))
  const highest = Math.max(...rows)
  const dots    = dotsOf(laid)
  const ball    = dots.findLast(dot => dot.kind === 'ahead')
  if (!ball) throw new Error(`${text} holds none of the letters ${logoLetters} Blue walks through`)
  const pixel = side / identity.IDENTITY.sprites.ball.frames[0]!.length

  return {
    ball     : { index: ball.index, size: pixel, x: ball.x - side / 2, y: ball.y - side / 2 },
    baseline : BASELINE * cell,
    blocks   : blocksOf(laid),
    dots     : dots.filter(dot => dot !== ball),
    lefts    : laid.letters.map(letter => letter.x * cell),
    view     : {
      height : (highest - Math.min(...rows) + 1) * cell + 2 * block.outset,
      width  : laid.width * cell + 2 * block.outset,
      x      : -block.outset,
      y      : (BASELINE - highest - 1) * cell - block.outset
    }
  }
}

/**
 * Reads the color `dot` takes on the ground `scheme` names, the scheme's ink
 * for a letter Blue does not walk through, and the step of Denim's ramp the
 * scheme gives the dot still ahead or the third of the trail a dot falls in.
 */
export function paintOf(dot: Dot, scheme: identity.Scheme): string {
  const colors = logoColors(scheme)
  if (dot.kind === 'trail') return colors.thirds[dot.third]!
  if (dot.kind === 'ahead') return colors.ahead
  return identity.IDENTITY.tones[scheme].ink
}

/**
 * Reads the third of a trail `span` steps long that `step` falls in, from 0 for
 * the oldest to 2 for the newest.
 */
export function thirdOf(step: number, span: number): number {
  return Math.min(2, Math.floor(3 * step / span))
}

/**
 * Reads the theme's color `dot` takes, which the stylesheet switches with the
 * scheme where `paintOf` reads one scheme's hex.
 */
export function toneOf(dot: Dot): Tone {
  return dot.kind === 'trail' ? `trail-${dot.third + 1}` as Tone : dot.kind
}
