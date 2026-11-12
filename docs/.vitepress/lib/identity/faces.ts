import { reactive } from 'vue'

import { useChoice } from '../widgets/choice.ts'
import { IDENTITY }  from './identity.ts'

/**
 * A role a face takes, the display face's, the body's, or code's.
 */
export type Role = keyof typeof IDENTITY.faces

/**
 * One weight of a face the site loads, its value, whether it is the italic,
 * and the label its swatch reads.
 */
export interface Weight {
  italic : boolean
  label  : string
  weight : number
}

/**
 * The roles in the order the page sets out their faces, the display face
 * first, as a heading opens what it heads.
 */
export const ROLES: readonly Role[] = ['display', 'body', 'code']

/**
 * The words each part a face sets reads, the heading, the paragraph around the
 * name of a setting, and the figures.
 */
export const WORDS = {
  figures : ['0.42', '1,024', '2.5M'],
  head    : 'The Walk to Oak’s Lab',
  inline  : 'max_episode_steps',
  lead    : 'Each episode starts in Blue’s bedroom and ends at the starter or after ',
  tail    : ' presses, and the reward pays for each square the episode has not reached before.'
} as const

/**
 * The step between two weights a range of the weight axis loads, as the
 * hundreds CSS names each weight by.
 */
const HUNDRED = 100

/**
 * Reads the weights `axes` loads a face at, written as the Google Fonts CSS API
 * takes them, each upright weight from the lightest, a range read as every
 * hundred across it, and then the italic at its lightest weight where the
 * face loads one.
 */
export function weightsOf(axes: string): Weight[] {
  const [names, tuples] = axes.split('@') as [string, string]
  const axis            = names.split(',')
  const loaded          = tuples.split(';').map(tuple => {
    const values = tuple.split(',')
    const [from, to = from] = values[axis.indexOf('wght')]!.split('..').map(Number) as [number, number?]
    const weights = Array.from({ length: (to - from) / HUNDRED + 1 }, (_, n) => from + n * HUNDRED)
    return { italic: values[axis.indexOf('ital')] === '1', weights }
  })
  const upright = [...new Set(loaded.filter(each => !each.italic).flatMap(each => each.weights))].toSorted((a, b) => a - b)
  const italic  = loaded.filter(each => each.italic).flatMap(each => each.weights)

  return [
    ...upright.map(weight => ({ italic: false, label: String(weight), weight })),
    ...italic.length > 0 ? [{ italic: true, label: 'Italic', weight: Math.min(...italic) }] : []
  ]
}

/**
 * The weights each role's face loads.
 */
export const WEIGHTS: Readonly<Record<Role, Weight[]>> = Object.fromEntries(
  ROLES.map(role => [role, weightsOf(IDENTITY.faces[role].axes)])) as Record<Role, Weight[]>

/**
 * Holds the weight a reader picks for each face, the lightest at first.
 *
 * Returns:
 *   The place in `WEIGHTS` each face stands at, and each face's swatches as a
 *   group of options.
 */
export function useFaces() {
  const at      = reactive(Object.fromEntries(ROLES.map(role => [role, 0])) as Record<Role, number>)
  const choices = Object.fromEntries(ROLES.map(role => [role, useChoice(WEIGHTS[role].map(each => each.label), label => {
    at[role] = WEIGHTS[role].findIndex(each => each.label === label)
  })])) as Record<Role, ReturnType<typeof useChoice<string>>>

  return { at, choices }
}
