import type { Identity } from '../identity/identity.ts'

/**
 * A plot laid out at one size in the pixels its view box counts: the right edge
 * and the floor of the region its marks fill, and the point `part` of `whole`
 * of the way across that region and up it.
 */
export interface Frame {
  end   : number
  floor : number
  x     : (part: number, whole: number) => number
  y     : (part: number, whole: number) => number
}

/**
 * Where a plot sets its labels: the shift of a value's baseline below its
 * value, the drop of a label below the floor, and the gap of a value's label
 * from the axis.
 */
export interface Labeling {
  baseline : number
  drop     : number
  gap      : number
}

/**
 * A label a plot sets in its drawing, its text, the point its anchor sits on,
 * and the side of the text that point holds.
 */
export interface PlotLabel {
  anchor : 'end' | 'middle' | 'start'
  text   : string
  x      : number
  y      : number
}

/**
 * The room each side of a plot's marks leaves, in the pixels its view box
 * counts.
 */
export type Sides = Readonly<Record<'bottom' | 'left' | 'right' | 'top', number>>

/**
 * The identity's stroke widths a plot draws its lines in.
 */
export type Strokes = Readonly<Identity['lengths']['strokes']>

/**
 * Where every plot sets its labels unless given otherwise.
 */
export const LABELING: Labeling = { baseline: 4, drop: 20, gap: 10 }

/**
 * Lays out a plot of `height` by `width` pixels inside the room `box` leaves,
 * each point rounded to a tenth of a pixel.
 */
export function frameOf(box: Sides, height: number, width: number): Frame {
  const floor = height - box.bottom
  const end   = width - box.right
  return {
    end   : end,
    floor : floor,
    x     : (part, whole) => round(box.left + (end - box.left) * part / whole),
    y     : (part, whole) => round(floor - (floor - box.top) * part / whole)
  }
}

/**
 * Lists the multiples of `every` from zero up to `upTo`.
 */
export function multiplesOf(every: number, upTo: number): number[] {
  return Array.from({ length: Math.floor(upTo / every) + 1 }, (_, n) => n * every)
}

/**
 * Rounds `value` to a tenth of a pixel.
 */
export function round(value: number): number {
  return Math.round(value * 10) / 10
}
