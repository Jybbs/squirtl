import { type PropType, computed, defineComponent } from 'vue'

import type * as rooms                                   from '../../../../lib/game/rooms.ts'
import type { Frame }                                    from '../../../../lib/methods/memory/play.ts'
import { LONGEST, type Role, SAYS, partsOf, pointedSay } from '../../../../lib/methods/memory/says.ts'

/**
 * The hue and weight each run of the sentence takes, the step in bold, the
 * bytes in the agent's Denim, and each payment in its term's hue.
 */
const ROLES: Readonly<Record<Role, string>> = {
  bytes     : 'font-semibold text-denim-text',
  goal      : 'font-semibold text-amethyst-text',
  milestone : 'font-semibold text-heath-text',
  novelty   : 'font-semibold text-fern-text',
  step      : 'font-bold'
}

/**
 * The sentence beneath the map for the step `frame` shows, or for the square
 * a pointer rests on as read at that step, on a band across the widget in the
 * code face's capitals, each run naming a mark in that mark's hue, laid over
 * the longest sentence any step takes so the band holds its height as the
 * episode plays.
 */
export const MemorySays = defineComponent({
  name: 'MemorySays',

  props: {
    frame   : { required: true, type: Object as PropType<Frame> },
    pointed : { default: null, type: Array as unknown as PropType<rooms.Square | null> }
  },

  setup: props => {
    const say = computed(() => props.pointed ? pointedSay(props.frame.place, props.pointed, props.frame.row) : SAYS[props.frame.row]!)
    return () => (
      <p aria-live="off" class="memory-says m-0 grid rounded-2 border-hairline border-rule bg-lift px-4 py-3 font-code text-small leading-relaxed font-medium tracking-caps text-ink uppercase">
        <span aria-hidden="true" class="invisible">{LONGEST}</span>
        <span>{partsOf(say.value, props.pointed !== null).map(([words, role]) => role ? <span class={ROLES[role]}>{words}</span> : words)}</span>
      </p>
    )
  }
})
