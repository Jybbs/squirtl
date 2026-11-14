import { codeWidth, setCaps, setLine } from '../cards/cards.ts'
import type { Walks }                  from '../front/learning/walks.ts'
import { IDENTITY, type Scheme }       from '../identity/identity.ts'
import { count }                       from '../widgets/numbers.ts'

/**
 * How the column beside the town sets each walk's count, its width, the left
 * and top of the first count and the pixels down to each next one, the rule in
 * the walk's mark, the room from the rule to the words, and the size and the
 * baseline of the episodes, the presses made so far, and the word after them.
 */
export interface Tally {
  figure : { size: number, y: number }
  inset  : number
  label  : { size: number, y: number }
  left   : number
  pitch  : number
  rule   : { height: number, width: number }
  top    : number
  width  : number
  word   : { gap: number, size: number }
}

/**
 * Draws the column of counts beside the town, each walk's rule and episodes in
 * its hue's mark and text step on GitHub's ground in `scheme`, and the presses
 * it has made by press `at` of the clock the walks share.
 */
export function tallyOf(at: number, height: number, scheme: Scheme, tally: Tally, walks: Walks): string {
  const { ink, quiet } = IDENTITY.tones[scheme]
  const room           = codeWidth(count(walks.longest), tally.figure.size)
  const counts         = walks.moments.map((moment, n) => {
    const done = Math.min(at, moment.presses)
    const hue  = walks.hues[n]!
    const x    = tally.left + tally.inset
    const y    = tally.top + n * tally.pitch
    const word = x + tally.word.gap + room
    return `<rect x="${tally.left}" y="${y}" width="${tally.rule.width}" height="${tally.rule.height}" `
         + `fill="${IDENTITY.marks[hue][scheme]}"/>`
         + setCaps(`${count(moment.episodes)} episodes`, {
           fill : IDENTITY.hues[hue][scheme].text,
           size : tally.label.size,
           x    : x,
           y    : y + tally.label.y
         })
         + setLine(count(done), {
           face : 'code',
           fill : ink,
           size : tally.figure.size,
           x    : x,
           y    : y + tally.figure.y
         })
         + setLine(done === 1 ? 'press' : 'presses', {
           face : 'code',
           fill : quiet,
           size : tally.word.size,
           x    : word,
           y    : y + tally.figure.y
         })
  })
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${tally.width}" height="${height}">`
       + `<rect width="${tally.width}" height="${height}" fill="${IDENTITY.github[scheme]}"/>${counts.join('')}</svg>`
}
