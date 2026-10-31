/**
 * A sprite's frame as its rows of Game Boy shades, each a string of digits from
 * 0, the lightest, to 3, the darkest.
 */
export type Grid = readonly string[]

/**
 * How `spriteMarkup` draws a frame, the left and top of its first pixel, the
 * side of one pixel, the fill of each shade from the lightest to the darkest,
 * and the opacity of the whole.
 */
export interface Placing {
  fills    : readonly string[]
  mirror?  : boolean
  opacity? : number
  size     : number
  x        : number
  y        : number
}

/**
 * A horizontal run of one row's pixels that share a shade, the unit a sprite
 * draws as one rectangle.
 */
export interface Run {
  shade : number
  width : number
  x     : number
  y     : number
}

/**
 * The shade a pixel left blank takes, which counts as the sprite's own white
 * where the sprite encloses it and as no pixel where it reaches the frame's
 * edge.
 */
const BLANK = '0'

/**
 * Finds the blank pixels connected to the frame's edge, which the Game Boy
 * leaves transparent, by flooding the blank pixels inward from every edge.
 */
function outside(rows: Grid): Set<number> {
  const side    = rows.length
  const reached = new Set<number>()
  const edge    = (i: number): [number, number][] => [[i, 0], [i, side - 1], [0, i], [side - 1, i]]
  const stack   = Array.from({ length: side }, (_, i) => edge(i)).flat()
  while (stack.length > 0) {
    const [x, y] = stack.pop()!
    const inside = x >= 0 && y >= 0 && x < side && y < side
    if (!inside || reached.has(y * side + x) || rows[y]![x] !== BLANK) continue
    reached.add(y * side + x)
    stack.push([x + 1, y], [x - 1, y], [x, y + 1], [x, y - 1])
  }
  return reached
}

/**
 * Splits a frame into the runs it draws, mirroring it to face the other way
 * where `mirror` is set, and leaving out every blank pixel the frame's edge
 * reaches.
 */
export function runsOf(grid: Grid, mirror = false): Run[] {
  const rows        = mirror ? grid.map(row => [...row].toReversed().join('')) : grid
  const clear       = outside(rows)
  const side        = rows.length
  const runs: Run[] = []
  rows.forEach((row, y) => {
    for (let x = 0; x < row.length;) {
      const out = clear.has(y * side + x)
      let end   = x + 1
      while (end < row.length && row[end] === row[x] && clear.has(y * side + end) === out) end++
      if (!out) runs.push({ shade: Number(row[x]), width: end - x, x, y })
      x = end
    }
  })
  return runs
}

/**
 * Draws a frame as SVG rectangles, one per run, each widened by a fraction of a
 * pixel so no seam shows between neighbors once the frame is scaled.
 */
export function spriteMarkup(grid: Grid, placing: Placing): string {
  const { fills, mirror = false, opacity = 1, size, x, y } = placing
  const rects = runsOf(grid, mirror).map(run =>
      `<rect x="${(x + run.x * size).toFixed(2)}" y="${(y + run.y * size).toFixed(2)}" `
    + `width="${(run.width * size + 0.3).toFixed(2)}" height="${(size + 0.3).toFixed(2)}" `
    + `fill="${fills[run.shade]}"/>`)
  return `<g opacity="${opacity}">${rects.join('')}</g>`
}
