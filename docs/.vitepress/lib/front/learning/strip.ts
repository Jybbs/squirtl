import { clamp } from '@vueuse/core'

import { multiplesOf }            from '../../drawing/plot.ts'
import { IDENTITY, hexOf }        from '../../identity/identity.ts'
import { fromMouse }              from '../../widgets/scrub.ts'
import { type Moment, longestOf } from '../learning.ts'

/**
 * Where the strip sets its lower rows in its own pixels, the top of its pins,
 * the baseline of its counts of presses, and its full height.
 */
export interface Rows {
  height : number
  labels : number
  pins   : number
}

/**
 * The strip's geometry in its own pixels: the stroke of a gridline, a band's
 * thickness, the clock chip's width, the radius of a corner, the presses
 * between two counts, the side of the hatch's cell, how far below the pins the
 * counts sit, the narrowest width it lays out at, how far its gridlines reach
 * above the bands, the side of a pin's sprite, the rows between bands, the side
 * of a pin's tile, and the top of the first band.
 */
export interface Strip {
  axis     : number
  band     : number
  chip     : number
  corner   : number
  every    : number
  hatch    : number
  label    : number
  least    : number
  overhang : number
  pin      : number
  row      : number
  tile     : number
  top      : number
}

/**
 * The strip's clock at one press, the left of its line and of its chip in the
 * strip's own pixels, beside a bit set for each walk ended by that press.
 */
export interface StripClock {
  ended : number
  left  : number
  now   : number
}

/**
 * The strip's geometry unless given otherwise, its strokes and its corners read
 * from the identity's lengths.
 */
export const STRIP: Strip = {
  axis     : IDENTITY.lengths.strokes.axis,
  band     : 5,
  chip     : 88,
  corner   : IDENTITY.lengths.radii['1'],
  every    : 50,
  hatch    : 4,
  label    : 16,
  least    : 120,
  overhang : 4,
  pin      : 14,
  row      : 8,
  tile     : 18,
  top      : 28
}

/**
 * Draws the hatch of the coin's presses in `fill` as the pattern named `id`,
 * each square cell of the strip's hatch holding a stripe half its width and
 * the cells turned through 45 degrees.
 */
export function hatchMarkup(fill: string, id: string, strip: Strip = STRIP): string {
  const side = strip.hatch
  return `<pattern id="${id}" patternUnits="userSpaceOnUse" width="${side}" height="${side}" `
       + `patternTransform="rotate(45)"><rect width="${side / 2}" height="${side}" fill="${fill}"/></pattern>`
}

/**
 * Draws the mark the key gives a band, the coin's presses hatched or the
 * table's solid, in Denim Deep on the light tile a chip's mark sits on, the
 * hatch taking the pattern named `id`.
 */
export function keyMark(id: string, sure: boolean, strip: Strip = STRIP): string {
  const ink  = hexOf('deep')
  const fill = sure ? ink : `url(#${id})`
  const band = `<rect x="1" y="${8 - strip.band / 2}" width="14" height="${strip.band}" fill="${fill}"/>`
  const defs = sure ? '' : `<defs>${hatchMarkup(ink, id, strip)}</defs>`
  return `<svg viewBox="0 0 16 16">${defs}${band}</svg>`
}

/**
 * Finds the walk whose band sits at `y` pixels down the strip, counting a
 * band's row as the band and the gap around it.
 *
 * Returns:
 *   The walk's index, or `undefined` where `y` falls above the first band or
 *   below the last of `walks`.
 */
export function rowAt(walks: number, y: number, strip: Strip = STRIP): number | undefined {
  const row = Math.floor((y - strip.top + (strip.row - strip.band) / 2) / strip.row)
  return row >= 0 && row < walks ? row : undefined
}

/**
 * Lays out the clock of a strip `wide` pixels across at the press `at` of
 * `moments`, its line where `at` falls along the longest walk, its chip
 * centered on the line but held inside the strip, and a bit set for each walk
 * that has ended by `at`.
 */
export function stripClockAt(
  at      : number,
  moments : readonly Moment[],
  wide    : number,
  strip   : Strip = STRIP
): StripClock {
  const now = wide * at / longestOf(moments)
  return {
    ended : moments.reduce((mask, walk, n) => at < walk.presses ? mask : mask | 1 << n, 0),
    left  : clamp(now - strip.chip / 2, 0, wide - strip.chip),
    now   : now
  }
}

/**
 * Lays out the strip's lower rows beneath the bands of `walks`, the pins just
 * below the last band and the counts of presses below the pins.
 */
export function stripRows(walks: number, strip: Strip = STRIP): Rows {
  const pins   = strip.top + strip.row * walks
  const labels = pins + strip.tile + strip.label
  return { height: labels + strip.overhang, labels, pins }
}

/**
 * Lists the presses the strip counts beneath its gridlines, every `every`
 * presses from the first up to `longest`.
 */
export function ticksOf(longest: number, strip: Strip = STRIP): number[] {
  return multiplesOf(strip.every, longest)
}

/**
 * Finds the walk whose band a mouse at `event` points at, reading the strip's
 * top from the element listening.
 *
 * Returns:
 *   The walk's index among `walks`, or `null` for a touch or a pen, which
 *   picks no walk out, and for a mouse beside every band.
 */
export function walkUnder(event: PointerEvent, walks: number, strip: Strip = STRIP): number | null {
  if (!fromMouse(event)) return null
  const top = (event.currentTarget as Element).getBoundingClientRect().top
  return rowAt(walks, event.clientY - top, strip) ?? null
}
