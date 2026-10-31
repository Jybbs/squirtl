import { spriteMarkup } from '../drawing/sprites.ts'
import * as identity    from '../identity/identity.ts'
import * as logo        from './logo.ts'

/**
 * The favicon's tile, its side and its corners' radius, beside the room the R
 * and the L keep from its sides and the top they are set at.
 */
const FAVICON = { corner: 18, inset: 8, side: 100, top: 25 }

/**
 * Draws the dots, the blocks, and the Poké Ball of `mark` in the colors
 * `scheme` gives them, every dot before the blocks so a block lies over the
 * edges of the dots beside it.
 */
function body(mark: logo.Mark, scheme: identity.Scheme): string {
  const fill   = logo.logoColors(scheme).block
  const dots   = mark.dots.map(dot =>
    `<circle cx="${dot.x}" cy="${dot.y}" r="${logo.dotRadius}" fill="${logo.paintOf(dot, scheme)}"/>`)
  const blocks = mark.blocks.map(block =>
      `<rect x="${block.x}" y="${block.y}" width="${block.side}" height="${block.side}" `
    + `rx="${block.radius}" fill="${fill}"/>`
    + poseOf(block, block.frame))

  return [...dots, ...blocks, ballOf(mark)].join('')
}

/**
 * Wraps `inner` as a standalone SVG viewed through `view` and labeled with the
 * project's name, carrying `attributes` on its root.
 */
function svgOf(inner: string, view: logo.ViewBox, attributes = ''): string {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBoxOf(view)}" role="img" `
       + `aria-label="${identity.IDENTITY.name}"${attributes}>${inner}</svg>`
}

/**
 * Writes `view` as the value of an SVG `viewBox`.
 */
export const viewBoxOf = (view: logo.ViewBox): string => `${view.x} ${view.y} ${view.width} ${view.height}`

/**
 * Draws the Poké Ball that ends the trail of `mark`, in the shades every sprite
 * takes.
 */
export function ballOf(mark: logo.Mark): string {
  const { ball } = identity.IDENTITY.sprites
  return spriteMarkup(ball.frames[0]!, { ...mark.ball, fills: identity.spriteShades })
}

/**
 * Draws Blue standing facing down in his block as each letter of the logo holds
 * him, the block in the theme's block color, so it follows the site's scheme.
 */
export function drawBlock(): string {
  const { block, sprite } = identity.IDENTITY.logo
  const frame             = identity.IDENTITY.sprites.player.frames[0]!
  const inset             = (block.size - sprite) / 2
  const tile              = `<rect width="${block.size}" height="${block.size}" rx="${block.radius}" `
                          + 'fill="var(--color-block)"/>'
  const pose = spriteMarkup(frame, {
    fills : identity.spriteShades,
    size  : sprite / frame.length,
    x     : inset,
    y     : inset
  })
  const view = { height: block.size, width: block.size, x: 0, y: 0 }
  return svgOf(tile + pose, view, ' shape-rendering="crispEdges"')
}

/**
 * Draws the favicon, the R and the L in the light ground's colors on an Athens
 * Gray tile with rounded corners.
 */
export function drawFavicon(): string {
  const { corner, inset, side, top } = FAVICON

  const mark   = logo.markOf(logo.logoLetters)
  const width  = side - 2 * inset
  const height = (width * mark.view.height / mark.view.width).toFixed(1)
  const tile   = `<rect width="${side}" height="${side}" rx="${corner}" fill="${identity.hexOf('ground')}"/>`
               + `<svg x="${inset}" y="${top}" width="${width}" height="${height}" `
               + `viewBox="${viewBoxOf(mark.view)}">${body(mark, 'light')}</svg>`

  return svgOf(tile, { height: side, width: side, x: 0, y: 0 }, ' shape-rendering="crispEdges"')
}

/**
 * Draws the icon the navigation bar shows, the R and the L alone with Blue in
 * each, in the colors `scheme` gives them.
 */
export function drawIcon(scheme: identity.Scheme): string {
  const mark = logo.markOf(logo.logoLetters)
  return svgOf(body(mark, scheme), mark.view, ' shape-rendering="crispEdges"')
}

/**
 * Draws the logo, the whole name in the display face's dots with Blue in the R
 * and the L, in the colors `scheme` gives it.
 */
export function drawLogo(scheme: identity.Scheme): string {
  const mark = logo.markOf(identity.IDENTITY.name)
  return svgOf(body(mark, scheme), mark.view)
}

/**
 * Draws Blue as he stands in `block` in `frame` of his sprite, in the shades
 * every sprite takes.
 */
export function poseOf(block: logo.Block, frame: number): string {
  const { player } = identity.IDENTITY.sprites
  const placing    = { ...block.sprite, fills: identity.spriteShades, mirror: block.mirror }
  return spriteMarkup(player.frames[frame]!, placing)
}
