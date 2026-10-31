import type { Badge, Hue } from '../identity/identity.ts'
import { runsOf }          from './sprites.ts'

/**
 * Draws `badge` in the four shades `hue` gives a badge, each a theme color that
 * switches with the scheme, cropped to a square around the runs it draws so it
 * sits centered in a round tile whatever room its grid leaves.
 */
export function badgeMarkup(badge: Badge, hue: Hue): string {
  const runs   = runsOf(badge.grid)
  const left   = Math.min(...runs.map(run => run.x))
  const right  = Math.max(...runs.map(run => run.x + run.width))
  const top    = Math.min(...runs.map(run => run.y))
  const bottom = Math.max(...runs.map(run => run.y)) + 1
  const side   = Math.max(right - left, bottom - top)
  const rects  = runs.map(run =>
      `<rect x="${run.x}" y="${run.y}" width="${run.width}" height="1" `
    + `fill="var(--color-${hue}-badge-${run.shade})"/>`)

  return `<svg viewBox="${(left + right - side) / 2} ${(top + bottom - side) / 2} ${side} ${side}" `
       + `shape-rendering="crispEdges" aria-hidden="true">${rects.join('')}</svg>`
}
