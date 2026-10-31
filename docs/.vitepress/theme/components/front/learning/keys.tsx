import { type PropType, defineComponent } from 'vue'

import type { Moment }   from '../../../../lib/front/learning.ts'
import { keyMark }       from '../../../../lib/front/learning/strip.ts'
import { fillsOf }       from '../../../../lib/front/learning/tints.ts'
import { spriteMark }    from '../../../../lib/game/actors.ts'
import type { Hue }      from '../../../../lib/identity/identity.ts'
import type { KeyEntry } from '../../../../lib/widgets/chips.ts'
import { count }         from '../../../../lib/widgets/numbers.ts'
import { Key }           from '../../kit/key.tsx'

/**
 * The names the key gives the strip's marks.
 */
const WORDS = {
  coin  : 'The coin’s presses',
  pin   : 'Where a walk stops',
  table : 'The table’s'
}

/**
 * Draws Blue in `hue` as the mark a walk's button and the key's pin carry.
 */
const blueMarkOf = (hue: Hue): string => spriteMark('player', fillsOf(hue))

/**
 * The buttons naming each walk by its episodes beside the presses it has made
 * by `at`, through the site's key, each picking its Blue out through `hover`
 * while a mouse rests on it and toggling him picked out through `pin` once
 * pressed, the buttons of the walks not picked out dimmed.
 */
export const WalkButtons = defineComponent({
  emits : ['hover', 'pin'],
  name  : 'WalkButtons',

  props: {
    at      : { required: true, type: Number },
    hues    : { required: true, type: Array as PropType<readonly Hue[]> },
    moments : { required: true, type: Array as PropType<readonly Moment[]> },
    picked  : { default: null, type: Number as PropType<number | null> },
    pinned  : { default: null, type: Number as PropType<number | null> }
  },

  setup: (props, { emit }) => {
    const marks = props.hues.map(hue => blueMarkOf(hue))

    return () => (
      <Key
        entries={props.moments.map((moment, n): KeyEntry => ({
          hue   : props.hues[n]!,
          label : `The walk after ${count(moment.episodes)} episodes`,
          mark  : marks[n]!,
          name  : `${count(moment.episodes)} episodes`,
          value : count(Math.min(props.at, moment.presses))
        }))}
        lit={props.picked}
        onHover={(n: number | null) => emit('hover', n)}
        onPress={(n: number) => emit('pin', n)}
        pressable
        pressed={props.pinned}
      />
    )
  }
})

/**
 * The key beneath the strip, naming the coin's hatch, the table's solid, and
 * the pin of Blue in `hue` where a walk stops, its patterns named from `id`.
 */
export const WalkKey = defineComponent({
  name: 'WalkKey',

  props: {
    hue : { required: true, type: String as PropType<Hue> },
    id  : { required: true, type: String }
  },

  setup: props => {
    const entries: KeyEntry[] = [
      { mark: keyMark(`${props.id}-coin`, false), name: WORDS.coin },
      { mark: keyMark(`${props.id}-table`, true), name: WORDS.table },
      { mark: blueMarkOf(props.hue), name: WORDS.pin }
    ]

    return () => <Key entries={entries} />
  }
})
