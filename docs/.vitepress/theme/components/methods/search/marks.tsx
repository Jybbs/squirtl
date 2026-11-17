import { type PropType, defineComponent } from 'vue'

import { termMark }  from '../../../../lib/game/actors.ts'
import type { Term } from '../../../../lib/game/episode.ts'
import { roleHue }   from '../../../../lib/identity/identity.ts'
import { CROSS }     from '../../../../lib/methods/search/key.ts'
import { HUES }      from '../../kit/hues.ts'

/**
 * The classes of the round tile the badge sits in, beside the ring of the
 * term's hue.
 */
const BADGE = 'absolute top-1 right-1 grid size-mark place-items-center rounded-full border-ring '
            + 'bg-athens-gray *:size-mark-art *:pixelated'

/**
 * The marks laid over one copy's screen: the cross over a dead copy, and the
 * badge of the flag its rollout set in a round tile ringed in the term's hue.
 */
export const SearchMarks = defineComponent({
  name: 'SearchMarks',

  props: {
    dead : { required: true, type: Boolean },
    term : { default: null, type: String as PropType<Term | null> }
  },

  setup: props => () => [
    props.dead
      ? <span
          aria-hidden="true"
          class="absolute inset-0 grid place-items-center text-ink *:size-7"
          innerHTML={CROSS}
        />
      : null,
    props.term === null
      ? null
      : <span
          aria-hidden="true"
          class={[BADGE, HUES[roleHue(props.term)].ring]}
          innerHTML={termMark(props.term)}
        />
  ]
})
