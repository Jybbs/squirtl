import { type Hue, type Role, roleHue } from '../identity/identity.ts'

/**
 * What a chip shows: its name, the hue it takes or the role whose hue it
 * takes, the game's mark, a quiet note, and its value.
 */
export interface ChipContent {
  name   : string
  hue?   : Hue | null
  mark?  : string
  note?  : string | null
  role?  : Role | 'none'
  value? : string | null
}

/**
 * One entry of a widget's key, what its chip shows beside the name a screen
 * reader reads where the entry is a button and the two figures it records
 * where the key sets figures under its heads.
 */
export interface KeyEntry extends ChipContent {
  figures? : KeyFigures
  label?   : string
}

/**
 * The two figures an entry records, or the two heads over them.
 */
export type KeyFigures = readonly [string, string]

/**
 * Reads the series hue a chip showing `content` takes, its own hue where it
 * names one and otherwise its role's.
 *
 * Returns:
 *   The hue, or `null` where the chip names no hue and its role is `none`.
 */
export function hueOf({ hue, role = 'none' }: Pick<ChipContent, 'hue' | 'role'>): Hue | null {
  return hue ?? (role === 'none' ? null : roleHue(role))
}
