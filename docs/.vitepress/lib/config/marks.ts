import { SCHEMES }                               from '../identity/palette.ts'
import * as drawings                             from '../marks/drawings.ts'
import { START_CARDS, drawStartCard, startPath } from '../readme/start.ts'

/**
 * Each mark the site carries, under its file's path relative to `docs/`, beside
 * the drawing written to that file, the logo under `assets/`, drawn for a light
 * and a dark ground, the README's cards under `assets/readme/` in each scheme,
 * and the icon and the favicon VitePress serves from the root of the deployment
 * under `public/`.
 */
export const MARKS: Readonly<Record<string, () => string>> = {
  'assets/logo-dark.svg'  : () => drawings.drawLogo('dark'),
  'assets/logo-light.svg' : () => drawings.drawLogo('light'),
  'public/favicon.svg'    : drawings.drawFavicon,
  'public/mark-dark.svg'  : () => drawings.drawIcon('dark'),
  'public/mark-light.svg' : () => drawings.drawIcon('light'),

  ...Object.fromEntries(START_CARDS.flatMap(card => SCHEMES.map(scheme =>
    [startPath(card, scheme), () => drawStartCard(card, scheme)])))
}
