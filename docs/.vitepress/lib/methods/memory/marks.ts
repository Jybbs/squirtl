import WORLD            from '../../art/world.json' with { type: 'json' }
import type { Flag }    from '../../game/flags.ts'
import type * as rooms  from '../../game/rooms.ts'
import { SQUARE }       from '../../game/screen.ts'
import { spriteShades } from '../../identity/identity.ts'
import SETTINGS         from '../../rendered/settings.json' with { type: 'json' }
import { fixed }        from '../../widgets/numbers.ts'

/**
 * A pixel shape drawn on a square, as runs of its left, its row, and its width
 * in the square's pixels.
 */
export type Shape = readonly (readonly [x: number, y: number, width: number])[]

/**
 * Where a room's map sits on the plate, the side of one of its squares, its
 * columns and rows, and its left, top, width, and height, in the plate's units.
 */
export interface Fit {
  cell   : number
  cols   : number
  height : number
  left   : number
  rows   : number
  top    : number
  width  : number
}

/**
 * Where the game sets a flag the reward reads, a square of a room or, for the
 * flag set on reaching a row, the whole row.
 */
export interface Site {
  flag  : Flag
  place : rooms.Place
  at?   : rooms.Square
  row?  : number
}

/**
 * The plate the map is drawn on, its square map area and the margins its
 * column and row numbers take, in the overlay's units.
 */
export const PLATE = (() => {
  const area = 288
  const left = 26
  const top  = 22
  return { area, height: top + area + 2, left, top, width: left + area + 2 }
})()

/**
 * The frames a square first reached takes to settle, about half a second at
 * the episode's pace, the steps over which its dot lightens, and the
 * milliseconds the bytes' square takes to glide to the next square.
 */
export const TIMING = { age: 40, glide: 160, settle: 48 } as const

/**
 * Where the game sets each flag the reward reads: Oak appears once `wYCoord`
 * reads 1 in Pallet Town, pret/pokered's `PalletTownDefaultScript`, and the
 * other three in the lab.
 */
export const SITES: readonly Site[] = [
  { flag: 'appeared', place: 'pallet', row: 1 },
  { at: [5, 3], flag: 'followed', place: 'lab' },
  { at: [5, 3], flag: 'asked', place: 'lab' },
  { at: [7, 3], flag: 'starter', place: 'lab' }
]

/**
 * Splits rows of pixels, `X` for one drawn, into the runs a shape draws,
 * centered in a square.
 */
function shapeOf(rows: readonly string[]): Shape {
  const off = (SQUARE - rows.length) / 2
  return rows.flatMap((row, y) => [...row.matchAll(/X+/gu)].map(run => [off + run.index, off + y, run[0].length] as const))
}

/**
 * The pixel shapes a square takes: the dot a square reached settles to, the
 * larger ones it pops in through, and the ring round the newest.
 */
export const SHAPES = {
  dot6   : shapeOf(['.XXXX.', 'XXXXXX', 'XXXXXX', 'XXXXXX', 'XXXXXX', '.XXXX.']),
  dot8   : shapeOf(['..XXXX..', '.XXXXXX.', 'XXXXXXXX', 'XXXXXXXX', 'XXXXXXXX', 'XXXXXXXX', '.XXXXXX.', '..XXXX..']),
  dot10  : shapeOf(['...XXXX...', '.XXXXXXXX.', '.XXXXXXXX.', 'XXXXXXXXXX', 'XXXXXXXXXX', 'XXXXXXXXXX', 'XXXXXXXXXX', '.XXXXXXXX.', '.XXXXXXXX.', '...XXXX...']),
  ring14 : shapeOf([
    '.....XXXX.....', '...XX....XX...', '..X........X..', '.X..........X.', '.X..........X.', 'X............X', 'X............X',
    'X............X', 'X............X', '.X..........X.', '.X..........X.', '..X........X..', '...XX....XX...', '.....XXXX.....'
  ])
} as const

/**
 * Reads the dot a square shows `settled` of the way through settling, popping
 * in large and settling small, the newest square keeping the middle size.
 */
export const dotOf = (settled: number, newest: boolean): Shape =>
  settled < 0.3 ? SHAPES.dot10 : settled < 0.65 || newest ? SHAPES.dot8 : SHAPES.dot6

/**
 * Fits the map of `place` into the plate's square area, centered on it.
 */
export function fitOf(place: rooms.Place): Fit {
  const { h: rows, w: cols } = WORLD[place]
  const cell                 = Math.min(PLATE.area / cols, PLATE.area / rows)
  const width                = cols * cell
  const height               = rows * cell
  return { cell, cols, height, left: PLATE.left + (PLATE.area - width) / 2, rows, top: PLATE.top + (PLATE.area - height) / 2, width }
}

/**
 * Draws `shape` as SVG rectangles in the current color.
 */
const shapeSvg = (shape: Shape): string =>
  shape.map(([x, y, width]) => `<rect x="${x}" y="${y}" width="${width}" height="1" fill="currentColor"/>`).join('')

/**
 * Draws a key mark on the game's lightest shade, as the map draws a square in
 * either scheme.
 */
const tileSvg = (inner: string): string =>
  `<svg viewBox="0 0 16 16" shape-rendering="crispEdges"><rect width="16" height="16" fill="${spriteShades[0]}"/>${inner}</svg>`

/**
 * Draws a flag's site in a key, dashed as the map draws it until it is set.
 */
const siteSvg = '<svg viewBox="0 0 16 16"><rect x="2" y="2" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="4 3"/></svg>'

/**
 * The key's entries, each the mark the map draws: a square reached, the newest,
 * the dashed squares where a milestone's or the starter's flag is set, and the
 * ring round the square the bytes name.
 */
export const KEY = [
  {
    mark : tileSvg(shapeSvg(SHAPES.dot6)),
    name : 'A square reached',
    note : `Each square the episode has stood on, its dot popping in as it is first reached and lightening as the steps since go by, the first step onto it paying ${fixed(SETTINGS.reward.novelty, 5)}`,
    role : 'novelty'
  },
  {
    mark : tileSvg(shapeSvg(SHAPES.dot8) + shapeSvg(SHAPES.ring14)),
    name : 'The newest square',
    note : 'The square the episode reached last, its dot ringed until it reaches the next',
    role : 'novelty'
  },
  { mark: siteSvg, name: 'A milestone flag', note: 'Where the game sets a milestone’s flag, dashed until it is set and filled once it is', role: 'milestone' },
  { mark: siteSvg, name: 'The starter flag', note: 'Where the game sets the starter’s flag, which ends the episode', role: 'starter' },
  {
    mark : '<svg viewBox="0 0 16 16"><path d="M8 -1V2M-1 8H2" stroke="currentColor" stroke-width="1.5" stroke-dasharray="3 3"/><rect x="2" y="2" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
    name : 'The bytes’ square',
    note : 'The square wXCoord and wYCoord name, its numbers at the map’s edges, gliding to each square the bytes name next',
    role : 'agent'
  }
] as const
