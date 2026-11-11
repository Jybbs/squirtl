import { termMark }                   from '../../game/actors.ts'
import { type EventFlag, eventFlags } from '../../game/episode.ts'
import EVENTS                         from '../../rendered/events.json' with { type: 'json' }
import * as numbers                   from '../../widgets/numbers.ts'
import * as sees                      from '../sees.ts'

/**
 * One event flag the network reads beside the mark of the term it pays.
 */
export interface FlagMark extends EventFlag {
  mark: string
}

/**
 * One gray frame of the observation, the steps it lies back from the newest
 * beside its name for a screen reader and the tag set over it.
 */
export interface FrameName {
  back  : number
  label : string
  tag   : string
}

/**
 * One event flag the network reads past the default goal, which the model of
 * the game never sets, its index in `wEventFlags` beside its name on a widget.
 */
export interface PastFlag {
  index : number
  name  : string
}

/**
 * The name a widget gives each event flag past the default goal, under the name
 * the package's `Event` gives the flag.
 */
const PAST = {
  EVENT_BATTLED_RIVAL_IN_OAKS_LAB : 'Battled the rival',
  EVENT_GOT_OAKS_PARCEL           : 'Got Oak’s parcel',
  EVENT_GOT_POKEDEX               : 'Got the Pokédex'
} as const

/**
 * Writes the shape and the bytes of each entry of the observation `observing`
 * sets out, the caption set beneath its drawing.
 */
export function captionsOf(
  observing : sees.Observing = sees.OBSERVING
): Record<keyof ReturnType<typeof sees.bytesOf>, string> {
  const { frame, grid, stack } = observing
  const bytes                  = sees.bytesOf(observing)
  return {
    flags  : `${bytes.flags}, in the order the opening sets them · ${numbers.count(bytes.flags)} bytes`,
    frames : `${stack} × ${frame.height} × ${frame.width}, `
           + `newest last · ${numbers.count(bytes.frames)} bytes`,
    grid   : `${grid} × ${grid}, Blue at the center · ${numbers.count(bytes.grid)} bytes`
  }
}

/**
 * Lists each event flag beside the mark of the term it pays, in the order the
 * network reads the flags.
 */
export function flagsOf(): FlagMark[] {
  return eventFlags.map(each => Object.assign({ mark: termMark(each.term) }, each))
}

/**
 * Names each gray frame of the observation `observing` sets out from the
 * oldest, the steps it lies back from the newest beside its name for a screen
 * reader and the tag set over it.
 */
export function frameNamesOf(observing: sees.Observing = sees.OBSERVING): FrameName[] {
  return Array.from({ length: observing.stack }, (_, i) => {
    const back = observing.stack - 1 - i
    if (back === 0) return { back, label: 'The frame of this step', tag: 't' }
    const label = `The frame ${numbers.counted(back, 'step')} before`
    return { back, label, tag: `t ${numbers.MINUS} ${back}` }
  })
}

/**
 * Lists each event flag past the default goal, which pays nothing toward it,
 * in the order the network reads the flags.
 */
export function pastOf(): PastFlag[] {
  return EVENTS.flatMap(({ index, name, term }) => term ? [] : [{ index, name: PAST[name as keyof typeof PAST] }])
}
