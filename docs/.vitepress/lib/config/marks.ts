import * as drawings from '../marks/drawings.ts'

/**
 * Each mark the site carries, under its file's path relative to `docs/`, beside
 * the drawing written to that file, the logo under `assets/`, drawn for a light
 * and a dark ground, and the icon and the favicon VitePress serves from the
 * root of the deployment under `public/`.
 */
export const MARKS: Readonly<Record<string, () => string>> = {
  'assets/logo-dark.svg'  : () => drawings.drawLogo('dark'),
  'assets/logo-light.svg' : () => drawings.drawLogo('light'),
  'public/favicon.svg'    : drawings.drawFavicon,
  'public/mark-dark.svg'  : () => drawings.drawIcon('dark'),
  'public/mark-light.svg' : () => drawings.drawIcon('light')
}
