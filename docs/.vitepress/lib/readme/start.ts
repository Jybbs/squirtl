import { fitCell }      from '../cards/cards.ts'
import { dotText }      from '../drawing/dots.ts'
import { spriteMarkup } from '../drawing/sprites.ts'
import { frameFor }     from '../game/actors.ts'
import * as identity    from '../identity/identity.ts'
import { logoColors }   from '../marks/logo.ts'

/**
 * How each card of Where to Start is drawn, in its image's pixels: the image's
 * size, the rounded card inside it, the room the word fits and its baseline's
 * left end, Blue's block, the room around him inside it, and where it stands,
 * and the trail's first dot, the pixels between its dots, their radius, the
 * runs of dots between its turns, and the pixels of the Poké Ball's sprite to
 * each of the sprite's own.
 */
interface Start {
  ball  : number
  block : { inset: number, radius: number, side: number, x: number, y: number }
  card  : { radius: number, x: number }
  image : { height: number, width: number }
  trail : { dot: number, legs: number, pitch: number, run: number, x: number, y: number }
  word  : { room: number, x: number, y: number }
}

/**
 * One card of the README's Where to Start, the section its link opens, the
 * word it shows, and the heading Blue's trail takes toward its Poké Ball, a
 * square up each turn where it climbs, a square down where it descends, and
 * none where it runs level.
 */
export interface StartCard {
  folder : identity.Folder
  rise   : -1 | 0 | 1
  word   : string
}

/**
 * Where to Start as the README carries it, each card an image of 260 by 150.
 */
const START: Start = {
  ball  : 1.5,
  block : { inset: 4, radius: 11, side: 40, x: 14, y: 80 },
  card  : { radius: 14, x: 4 },
  image : { height: 150, width: 260 },
  trail : { dot: 6, legs: 3, pitch: 18, run: 3, x: 66, y: 100 },
  word  : { room: 200, x: 20, y: 46 }
}

/**
 * The cards of Where to Start in the order the README sets them abreast,
 * Understand climbing to the Methods page, Check running level to the Results
 * section, and Run descending to the Commands page.
 */
export const START_CARDS: readonly StartCard[] = [
  { folder: 'methods', rise: 1, word: 'Understand' },
  { folder: 'results', rise: 0, word: 'Check' },
  { folder: 'commands', rise: -1, word: 'Run' }
]

/**
 * Lays out the dots of the trail heading as `rise` sets it, from its first dot
 * eastward a run at a time, a square up or down between runs.
 */
function trailOf(rise: number, trail: Start['trail']): [x: number, y: number][] {
  const dots: [number, number][] = [[trail.x, trail.y]]
  for (let leg = 0; leg < trail.legs; leg++) {
    const [x, y] = dots.at(-1)!
    if (leg > 0 && rise !== 0) dots.push([x, y - rise * trail.pitch])
    for (let step = 1; step <= trail.run; step++) {
      const [left, top] = dots.at(-1)!
      dots.push([left + trail.pitch, top])
    }
  }
  return dots
}

/**
 * Draws the card of `card` in `scheme`: its word in the display face in its
 * section's mark on the section's Shade 1, Blue walking out of the logo's
 * block, and his trail in the section's ramp from the oldest third to the
 * newest, ending on a Poké Ball in the section's shades.
 */
export function drawStartCard(card: StartCard, scheme: identity.Scheme): string {
  const { ball, block, image, trail, word } = START
  const hue                                 = identity.sectionHue(card.folder)
  const steps                               = identity.IDENTITY.hues[hue][scheme]
  const mark                                = identity.IDENTITY.marks[hue][scheme]
  const shades                              = steps.shades
  const dark                                = scheme === 'dark'
  const thirds                              = [shades[3]!, mark, dark ? steps.pale : steps.deep]
  const ballFills                           = [
    dark ? steps.pale : identity.hexOf('ground-lift'), shades[dark ? 3 : 2]!, mark, identity.hexOf('dark')
  ]
  const cell     = Math.min(...START_CARDS.map(each => fitCell(each.word, Number.POSITIVE_INFINITY, word.room)))
  const dots     = trailOf(card.rise, trail)
  const [end]    = dots.splice(-1) as [[number, number]]
  const sprite   = identity.IDENTITY.sprites.ball.frames[0]!
  const ballSide = ball * sprite.length
  const player   = frameFor('player', 'right', 'walking')

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${image.width}" height="${image.height}" `
       + `viewBox="0 0 ${image.width} ${image.height}" role="img" aria-label="${card.word}">`
       + `<rect x="${START.card.x}" width="${image.width - 2 * START.card.x}" height="${image.height}" `
       + `rx="${START.card.radius}" fill="${shades[0]}"/>`
       + dotText(card.word, { cell, fill: mark, x: word.x, y: word.y })
       + dots.map(([x, y], n) =>
           `<circle cx="${x}" cy="${y}" r="${trail.dot}" fill="${thirds[Math.floor(3 * n / dots.length)]}"/>`)
         .join('')
       + spriteMarkup(sprite, {
         fills : ballFills,
         size  : ball,
         x     : end[0] - ballSide / 2,
         y     : end[1] - ballSide / 2
       })
       + `<rect x="${block.x}" y="${block.y}" width="${block.side}" height="${block.side}" `
       + `rx="${block.radius}" fill="${logoColors(scheme).block}"/>`
       + spriteMarkup(player.grid, {
         fills  : identity.spriteShades,
         mirror : player.mirrored,
         size   : (block.side - 2 * block.inset) / player.grid.length,
         x      : block.x + block.inset,
         y      : block.y + block.inset
       })
       + '</svg>'
}

/**
 * Reads the path under `docs/` of the card of `card` in `scheme`.
 */
export const startPath = (card: StartCard, scheme: identity.Scheme): string =>
  `assets/readme/${card.word.toLowerCase()}-${scheme}.svg`
