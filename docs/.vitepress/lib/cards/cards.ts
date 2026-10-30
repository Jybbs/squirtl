import type { PageData } from 'vitepress'

import type { ProjectFacts }     from '../config/manifest.ts'
import { isFrontPage }           from '../config/pages.ts'
import { dotText, layout }       from '../drawing/dots.ts'
import { IDENTITY, type Scheme } from '../identity/identity.ts'

/**
 * A page the site builds, as far as its card reads it, the fields `cardPath`
 * reads beside the page's title.
 */
export type CardPage = Pick<PageData, 'isNotFound' | 'relativePath' | 'title'>

/**
 * The facts a card's edition plate names, the project's version and the host
 * the site serves from.
 */
export type Edition = Pick<ProjectFacts, 'host' | 'version'>

/**
 * A face a card sets its words in, as the identity names it.
 */
type Face = keyof typeof IDENTITY.faces

/**
 * How `setLine` sets one line of text, its fill, its size, and the left end of
 * its baseline, beside its face, whether it is italic, and the room added after
 * each character.
 */
interface Lettering {
  fill     : string
  size     : number
  x        : number
  y        : number
  face?    : Face
  italic?  : boolean
  spacing? : number
}

/**
 * A point on a card, in the card's pixels.
 */
export interface Point {
  x : number
  y : number
}

/**
 * The rows of cells a capital of the display face spans, the height a line set
 * in its dots stands above its baseline.
 */
export const CAPITAL = 6

/**
 * The size every preview card is drawn at, in pixels, the 1.91:1 a shared
 * link's card takes where Open Graph and Twitter's cards are read.
 */
export const CARD = { height: 630, width: 1200 } as const

/**
 * How the edition plate is drawn, its height and its padding, its outer frame
 * and its inner one, the version in dots, the rule after it, and the words
 * naming the host, `advance` being the code face's advance as a share of its
 * size.
 */
const EDITION = {
  advance : 0.6,
  frames  : { corners: [6, 3], inset: 7, strokes: [2, 1] },
  height  : 92,
  pad     : 24,
  rule    : { gap: 10, height: 48 },
  version : { baseline: 60, cell: 4.4 },
  words   : { baseline: 55, gap: 22, size: 24 }
}

/**
 * The characters a card's text escapes, beside the entity written for each.
 */
const ENTITIES = { '&': '&amp;', '<': '&lt;', '>': '&gt;' } as const

/**
 * The room every card keeps, its words opening `top` below its top edge and
 * `inset` in from its left, which is also the room below its edition plate,
 * with `gap` kept between the words and the art.
 */
export const MARGIN = { gap: 40, inset: 72, top: 96 }

/**
 * The top of the edition plate on every card, the margin's inset above the
 * card's foot.
 */
const plateTop = CARD.height - MARGIN.inset - EDITION.height

/**
 * The height of the edition plate's middle, the line a section card marks the
 * sections on.
 */
export const plateLine = plateTop + EDITION.height / 2

/**
 * Reports whether the page is one of the two that show the site's own card, the
 * front page and the page a reader meets at a missing address.
 */
const shared = (page: Pick<PageData, 'isNotFound' | 'relativePath'>): boolean =>
  Boolean(page.isNotFound) || isFrontPage(page.relativePath)

/**
 * Builds the path of the card a link to the page shows, under the root of the
 * built site, the front page and the page at a missing address sharing the
 * site's card.
 */
export function cardPath(page: Pick<PageData, 'isNotFound' | 'relativePath'>): string {
  return shared(page) ? 'cards/site.png' : `cards/${page.relativePath.replace(/\.md$/u, '.png')}`
}

/**
 * Draws the edition plate at the foot of the card, the project's version in
 * dots beside the host the site serves from, framed twice in the quiet ink of
 * `scheme`.
 */
export function drawPlate(facts: Edition, scheme: Scheme): string {
  const { advance, frames, height, pad, rule, version, words } = EDITION
  const { ink, quiet } = IDENTITY.tones[scheme]
  const [outer, inner] = frames.corners as [number, number]
  const [thick, thin]  = frames.strokes as [number, number]
  const { inset: x }   = MARGIN
  const host           = `Edition · ${facts.host}`
  const named          = Math.ceil(host.length * words.size * (advance + IDENTITY.lengths.track))
  const figure         = layout(facts.version).width * version.cell
  const width          = 2 * pad + figure + words.gap + named
  const left           = x + pad + figure

  return `<rect x="${x}" y="${plateTop}" width="${width}" height="${height}" rx="${outer}" fill="none" `
       + `stroke="${quiet}" stroke-width="${thick}"/>`
       + `<rect x="${x + frames.inset}" y="${plateTop + frames.inset}" width="${width - 2 * frames.inset}" `
       + `height="${height - 2 * frames.inset}" rx="${inner}" fill="none" stroke="${quiet}" `
       + `stroke-width="${thin}"/>`
       + dotText(facts.version, { cell: version.cell, fill: ink, x: x + pad, y: plateTop + version.baseline })
       + `<rect x="${left + rule.gap}" y="${plateTop + (height - rule.height) / 2}" width="1" `
       + `height="${rule.height}" fill="${quiet}"/>`
       + setCaps(host, { fill: ink, size: words.size, x: left + words.gap, y: plateTop + words.baseline })
}

/**
 * Sizes the cell `text` fits `room` at in the display face's dots, to the tenth
 * of a pixel below and at most `most`, counting the fifth of a cell the outer
 * dots reach past the text's cells.
 */
export function fitCell(text: string, most: number, room: number): number {
  return Math.min(most, Math.floor(10 * room / (layout(text).width + 0.2)) / 10)
}

/**
 * Sets `text` in capitals in the code face, tracked as the identity tracks
 * capitals.
 */
export function setCaps(text: string, lettering: Omit<Lettering, 'face' | 'italic' | 'spacing'>): string {
  const spacing = lettering.size * IDENTITY.lengths.track
  return setLine(text.toUpperCase(), { ...lettering, face: 'code', spacing })
}

/**
 * Sets `text` as one line of SVG text as `lettering` sets it, in the body face
 * unless it names another, escaping the characters XML reads as markup.
 */
export function setLine(text: string, lettering: Lettering): string {
  const { face = 'body', fill, italic = false, size, spacing, x, y } = lettering
  const escaped = text.replaceAll(/[&<>]/gu, char => ENTITIES[char as keyof typeof ENTITIES])
  const slant   = italic ? ' font-style="italic"' : ''
  const tracked = spacing ? ` letter-spacing="${spacing.toFixed(1)}"` : ''

  return `<text x="${x}" y="${y}" font-family="${IDENTITY.faces[face].stack}" font-size="${size}" `
       + `fill="${fill}"${slant}${tracked}>${escaped}</text>`
}

/**
 * Splits `text` into two lines at the space that leaves their lengths closest,
 * the earlier space where two leave them as close, and leaves a text of one
 * word whole on the first line.
 */
export function splitInTwo(text: string): [string, string] {
  const words  = text.split(' ')
  const halves = (at: number): [string, string] => [words.slice(0, at).join(' '), words.slice(at).join(' ')]
  const gap    = (at: number): number => {
    const [first, second] = halves(at)
    return Math.abs(first.length - second.length)
  }
  return halves(words.keys().drop(1).reduce((best, at) => gap(at) < gap(best) ? at : best, words.length))
}

/**
 * Wraps `body` as a whole card, the size a shared link shows, on the ground
 * `scheme` names.
 */
export function wrapCard(body: string, scheme: Scheme): string {
  const { height, width } = CARD
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" `
       + `viewBox="0 0 ${width} ${height}"><rect width="${width}" height="${height}" `
       + `fill="${IDENTITY.tones[scheme].ground}"/>${body}</svg>`
}
