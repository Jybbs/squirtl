import { type PropType, defineComponent } from 'vue'

import type { RoomImages }    from '../../../../lib/game/images.ts'
import { MILESTONE, carries } from '../../../../lib/methods/search/key.ts'
import type { Shown }         from '../../../../lib/methods/search/moments.ts'
import { fixed }              from '../../../../lib/widgets/numbers.ts'
import { Chip }               from '../../kit/chip.tsx'
import { LABEL }              from '../../kit/widget.ts'
import { SearchCopy }         from './copy.tsx'

/**
 * One group of copies of the game: its name, the reward chip holding the most
 * any of its copies' lineages holds, and its copies, each dimmed where the key
 * entry `lit` names a mark it does not carry.
 */
export const SearchGroup = defineComponent({
  name: 'SearchGroup',

  props: {
    copies : { required: true, type: Array as PropType<readonly Shown[]> },
    images : { required: true, type: Object as PropType<RoomImages> },
    lit    : { default: null, type: Number as PropType<number | null> },
    n      : { required: true, type: Number }
  },

  setup: props => () => (
    <li class="grid gap-2">
      <div class="flex items-center justify-between gap-3">
        <span class={LABEL}>Group {props.n}</span>
        <Chip
          mark={MILESTONE}
          name="Reward"
          role="milestone"
          value={fixed(Math.max(...props.copies.map(each => each.total)), 4)}
        />
      </div>
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {props.copies.map((shown, slot) => (
          <SearchCopy
            dim={props.lit !== null && !carries(shown, props.lit)}
            images={props.images}
            label={`Copy ${slot + 1} of group ${props.n}`}
            shown={shown}
          />
        ))}
      </div>
    </li>
  )
})
