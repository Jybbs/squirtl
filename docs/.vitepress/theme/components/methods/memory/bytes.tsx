import { type PropType, defineComponent } from 'vue'

import { termMark }    from '../../../../lib/game/actors.ts'
import type * as rooms from '../../../../lib/game/rooms.ts'
import { ADDRESS, MAPS, ROOMS, SECOND, TRACE, address, byte } from '../../../../lib/methods/memory.ts'
import type { Frame }  from '../../../../lib/methods/memory/play.ts'
import { Chip }        from '../../kit/chip.tsx'
import { DETAIL }      from '../../kit/widget.ts'

/**
 * The room each map number names.
 */
const PLACES = new Map(Object.entries(MAPS).map(([place, map]) => [map, place as rooms.Place]))

/**
 * The bytes the reward reads after the step `frame` shows, each a chip in its
 * term's hue beside its address: `wCurMap` naming the room, `wXCoord` and
 * `wYCoord` the square, which follow a pointed square, and the two bytes of
 * `wEventFlags` holding the flags.
 */
export const MemoryBytes = defineComponent({
  name: 'MemoryBytes',

  props: {
    frame  : { required: true, type: Object as PropType<Frame> },
    square : { required: true, type: Array as unknown as PropType<rooms.Square> }
  },

  setup: props => () => {
    const { bytes } = TRACE[props.frame.row]!
    const rows      = [
      { name: 'wCurMap', reads: `${address(ADDRESS.map)} · ${ROOMS[PLACES.get(props.frame.map)!]}`, term: 'novelty', value: byte(props.frame.map) },
      { name: 'wXCoord', reads: `${address(ADDRESS.x)} · the column`, term: 'novelty', value: byte(props.square[0]) },
      { name: 'wYCoord', reads: `${address(ADDRESS.y)} · the row`, term: 'novelty', value: byte(props.square[1]) },
      {
        name  : 'wEventFlags',
        reads : `${address(ADDRESS.flags)} and ${address(SECOND)}`,
        term  : 'milestone',
        value : `${byte(bytes.get(ADDRESS.flags)!)} ${byte(bytes.get(SECOND)!)}`
      }
    ] as const

    return (
      <div class="memory-bytes grid gap-2">
        {rows.map(({ name, reads, term, value }) => (
          <div class="grid gap-0.5" key={name}>
            <Chip class="memory-code w-full" mark={termMark(term)} name={name} role={term} value={value} />
            <span class={[DETAIL, 'pl-3 whitespace-nowrap']}>{reads}</span>
          </div>
        ))}
      </div>
    )
  }
})
