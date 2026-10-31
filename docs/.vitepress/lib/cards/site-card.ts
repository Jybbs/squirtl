import TOWN             from '../art/town.json' with { type: 'json' }
import { dotText }      from '../drawing/dots.ts'
import { spriteMarkup } from '../drawing/sprites.ts'
import * as identity    from '../identity/identity.ts'
import * as logo        from '../marks/logo.ts'
import * as cards       from './cards.ts'

/**
 * Where Pallet Town sits on the site's card, the left and top of its image, its
 * width, the side of one of its squares, and the center of each square of the
 * walk to Oak's lab, in the card's pixels.
 */
interface TownPlacement {
  centers : readonly cards.Point[]
  left    : number
  square  : number
  top     : number
  width   : number
}

/**
 * How the site's card draws Pallet Town and the walk to Oak's lab, the card's
 * pixels to one of the town's and the room kept at its right, each length of
 * the walk as a share of one square of the town, the halo around each trail
 * dot, the veil fading the town in behind the words, the frame Blue stands in,
 * and the name and the tagline set beside it.
 */
const SITE = {
  block   : 1.24,
  corner  : 0.34,
  dot     : 0.3,
  frame   : 0,
  goal    : 0.7,
  halo    : 5,
  margin  : 34,
  most    : 10,
  scale   : 1.95,
  tagline : { drop: 58, lead: 44, size: 33 },
  veil    : [[0, 1], [0.16, 0.35], [1, 0]]
}

/**
 * Places Pallet Town at the card's right, `SITE.margin` in from its edge and
 * centered from its top to its foot.
 */
function placeTown(): TownPlacement {
  const { margin, scale } = SITE

  const square  = TOWN.square * scale
  const width   = TOWN.width * scale
  const left    = cards.CARD.width - width - margin
  const top     = (cards.CARD.height - TOWN.height * scale) / 2
  const centers = TOWN.walk.map(([x, y]) => ({ x: left + (x! + 0.5) * square, y: top + (y! + 0.5) * square }))

  return { centers, left, square, top, width }
}

/**
 * Sets the name in dots, its R and its L in the trail's newest color, above the
 * tagline in two italic lines of the body face.
 */
function siteWords(place: TownPlacement, scheme: identity.Scheme): string {
  const { ink }              = identity.IDENTITY.tones[scheme]
  const { gap, inset, top }  = cards.MARGIN
  const { drop, lead, size } = SITE.tagline

  const newest   = logo.logoColors(scheme).thirds[2]!
  const colors   = Array.from(identity.IDENTITY.name, char => logo.logoLetters.includes(char) ? newest : ink)
  const cell     = cards.fitCell(identity.IDENTITY.name, SITE.most, place.left - inset - gap)
  const baseline = top + cards.CAPITAL * cell
  const lines    = cards.splitInTwo(identity.IDENTITY.tagline).map((text, i) =>
    cards.setLine(text, { fill: ink, italic: true, size, x: inset, y: baseline + drop + i * lead }))

  const name = dotText(identity.IDENTITY.name, {
    cell : cell,
    fill : (_column, _row, letter) => colors[letter]!,
    x    : inset,
    y    : baseline
  })

  return name + lines.join('')
}

/**
 * Draws Pallet Town in the colors of `scheme` beneath a veil that fades it in
 * from the ground at its left edge.
 */
function townImage(place: TownPlacement, scheme: identity.Scheme): string {
  const { left, top, width } = place
  const { ground }           = identity.IDENTITY.tones[scheme]

  const id    = `veil-${scheme}`
  const stops = SITE.veil.map(([offset, opacity]) =>
    `<stop offset="${offset}" stop-color="${ground}" stop-opacity="${opacity}"/>`)

  return `<image href="${TOWN.image[scheme]}" x="${left}" y="${top}" width="${width}" `
       + `height="${TOWN.height * SITE.scale}" image-rendering="optimizeSpeed" preserveAspectRatio="none"/>`
       + `<defs><linearGradient id="${id}" x1="0" x2="1">${stops.join('')}</linearGradient></defs>`
       + `<rect x="${left}" y="0" width="${width + SITE.margin}" height="${cards.CARD.height}" fill="url(#${id})"/>`
}

/**
 * Draws a dot on every square of the walk between its ends, each in the color
 * of the third of the walk it falls in and haloed in the ground.
 */
function trailDots(place: TownPlacement, scheme: identity.Scheme): string {
  const { ground } = identity.IDENTITY.tones[scheme]
  const thirds     = logo.logoColors(scheme).thirds
  const trail      = place.centers.slice(1, -1)
  const radius     = (place.square * SITE.dot).toFixed(1)

  return trail
    .map((point, i) => `<circle cx="${point.x.toFixed(1)}" cy="${point.y.toFixed(1)}" r="${radius}" `
                     + `fill="${thirds[logo.thirdOf(i, trail.length)]}" stroke="${ground}" `
                     + `stroke-width="${SITE.halo}" paint-order="stroke"/>`)
    .join('')
}

/**
 * Draws the walk's two ends, Blue standing in his block at its start and the
 * Poké Ball on a disc of the ground at its end.
 */
function walkEnds(place: TownPlacement, scheme: identity.Scheme): string {
  const { block, corner, goal } = SITE
  const { square }              = place

  const start = place.centers[0]!
  const end   = place.centers.at(-1)!
  const side  = square * block
  const frame = identity.IDENTITY.sprites.player.frames[SITE.frame]!
  const ball  = identity.IDENTITY.sprites.ball.frames[0]!
  const fills = identity.spriteShades
  const blue  = { fills, size: square / frame.length, x: start.x - square / 2, y: start.y - square / 2 }
  const disc  = { fills, size: side / ball.length, x: end.x - side / 2, y: end.y - side / 2 }

  return `<rect x="${(start.x - side / 2).toFixed(1)}" y="${(start.y - side / 2).toFixed(1)}" `
       + `width="${side.toFixed(1)}" height="${side.toFixed(1)}" rx="${(square * corner).toFixed(1)}" `
       + `fill="${logo.logoColors(scheme).block}"/>`
       + spriteMarkup(frame, blue)
       + `<circle cx="${end.x.toFixed(1)}" cy="${end.y.toFixed(1)}" r="${(square * goal).toFixed(1)}" `
       + `fill="${identity.IDENTITY.tones[scheme].ground}"/>`
       + spriteMarkup(ball, disc)
}

/**
 * Draws the site's own card, Pallet Town in Denim with the walk to Oak's lab as
 * the trail, Blue in his block at its start and the Poké Ball at its end,
 * beside the name in dots, the tagline, and the edition plate, on the ground
 * `scheme` names.
 */
export function drawSiteCard(facts: cards.Edition, scheme: identity.Scheme = 'dark'): string {
  const place = placeTown()
  const art   = townImage(place, scheme) + trailDots(place, scheme) + walkEnds(place, scheme)
  return cards.wrapCard(art + siteWords(place, scheme) + cards.drawPlate(facts, scheme), scheme)
}
