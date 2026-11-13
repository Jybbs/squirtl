import { type Hue, IDENTITY, type Scheme, type Token, contrast } from './identity.ts'

/**
 * One color the identity names, its token, its name, its hex, and the table it
 * sits in.
 */
export interface Named {
  hex   : string
  name  : string
  table : Table
  token : Token
}

/**
 * One step of a hue's ramp on one ground, its name and its hex.
 */
export interface Step {
  hex  : string
  name : string
}

/**
 * The tables of the identity a named color sits in.
 */
export type Table = 'colors' | 'neutrals' | 'ramp'

/**
 * How far a color stands from its ground, enough for text, enough for a mark
 * alone, or neither, as the 4.5:1 and the 3:1 WCAG 2.2 sets.
 */
export type Level = 'fill' | 'mark' | 'text'

/**
 * The tables of named colors in the order the palette lists them, each beside
 * its title.
 */
export const TABLES: readonly { table: Table, title: string }[] = [
  { table: 'colors', title: 'Colors' },
  { table: 'neutrals', title: 'Neutrals' },
  { table: 'ramp', title: 'Denim’s ramp' }
]

/**
 * Every color the identity names, table by table in the order of `TABLES`.
 */
export const NAMED: readonly Named[] = TABLES.flatMap(({ table }) =>
  Object.entries(IDENTITY[table]).map(([token, color]) => ({ hex: color.hex, name: color.name, table, token: token as Token })))

/**
 * The color schemes, the light one first, as the palette sets them out.
 */
export const SCHEMES: readonly Scheme[] = ['light', 'dark']

/**
 * The ground each color scheme sets every page on.
 */
export const GROUNDS = Object.fromEntries(SCHEMES.map(scheme => [scheme, groundOf(scheme)])) as Readonly<Record<Scheme, { hex: string, name: string }>>

/**
 * Finds the color the identity names `token`.
 */
export function namedOf(token: string): Named {
  return NAMED.find(each => each.token === token)!
}

/**
 * Reads the ground `scheme` sets every page on, its hex and its name.
 */
function groundOf(scheme: Scheme): { hex: string, name: string } {
  const { hex, name } = namedOf(IDENTITY.schemes[scheme].ground)
  return { hex, name }
}

/**
 * Finds the hue whose own color is `token`, or `null` for a color carrying no
 * ramp.
 */
export function hueOfToken(token: Token): Hue | null {
  const found = Object.entries(IDENTITY.hues).find(([, hue]) => hue.token === token)
  return found ? found[0] as Hue : null
}

/**
 * Reads the steps of `hue`'s ramp on `scheme`'s ground, its four shades from
 * nearest the ground and then its text step.
 */
export function stepsOf(hue: Hue, scheme: Scheme): Step[] {
  const ramp = IDENTITY.hues[hue][scheme]
  return [...ramp.shades.map((hex, n) => ({ hex, name: `Shade ${n + 1}` })), { hex: ramp.text, name: 'Text' }]
}

/**
 * Reads how far a color at the contrast ratio `ratio` stands from its ground,
 * as `Level` names it.
 */
export function levelOf(ratio: number): Level {
  return ratio >= 4.5 ? 'text' : ratio >= 3 ? 'mark' : 'fill'
}

/**
 * Chooses the ground's hex that reads on the fill `hex`, whichever of the two
 * grounds stands farther from it.
 */
export function inkOn(hex: string): string {
  return contrast(hex, GROUNDS.dark.hex) >= contrast(hex, GROUNDS.light.hex) ? GROUNDS.dark.hex : GROUNDS.light.hex
}

/**
 * Places a contrast ratio on a scale from 1 to 21 measured in its logarithm,
 * as a share from 0 to 1.
 */
export function meterOf(ratio: number): number {
  return Math.log(ratio) / Math.log(21)
}

/**
 * The fills Blue's sprite takes in `hue`'s ramp on `scheme`'s ground, from the
 * Game Boy's lightest shade to its darkest, the ground inside him, the second
 * shade, the hue's mark, and the text step for his outline.
 */
export function blueFills(hue: Hue, scheme: Scheme): string[] {
  const ramp = IDENTITY.hues[hue][scheme]
  return [GROUNDS[scheme].hex, ramp.shades[1]!, IDENTITY.marks[hue][scheme], ramp.text]
}

/**
 * Every step of a ramp a reader may pick, by the ground it sits on and its
 * place from nearest the ground, the text step last.
 */
export const STEPS = SCHEMES.flatMap(scheme => [0, 1, 2, 3, 4].map(n => `${scheme}-${n}` as const))

/**
 * A step of a ramp a reader picks, by its ground and its place.
 */
export type Picked = typeof STEPS[number]

/**
 * What the palette's card shows, the hex, the name, and what the hex is.
 */
export interface Shown {
  hex  : string
  name : string
  what : string
}

/**
 * Reads what the card shows for the color `named` and the step `picked` of its
 * hue's ramp, the step where one is picked and the color itself otherwise.
 */
export function shownOf(named: Named, picked: Picked | null): Shown {
  const hue = hueOfToken(named.token)
  if (hue === null || picked === null) return { hex: named.hex, name: named.name, what: named.token }
  const [scheme, n] = picked.split('-') as [Scheme, string]
  const step        = stepsOf(hue, scheme)[Number(n)]!
  return { hex: step.hex, name: `${named.name} ${step.name}`, what: `on ${GROUNDS[scheme].name}` }
}
