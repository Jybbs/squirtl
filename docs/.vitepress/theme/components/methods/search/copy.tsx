import { type PropType, defineComponent, onMounted, ref, watch } from 'vue'

import type { RoomImages }    from '../../../../lib/game/images.ts'
import { padMark, pressName } from '../../../../lib/game/pad.ts'
import { SCREEN }             from '../../../../lib/game/screen.ts'
import type { Shown }         from '../../../../lib/methods/search/moments.ts'
import { CopyScreen }         from '../../../../lib/methods/search/screens.ts'
import { useCanvasLoop }      from '../../../../lib/widgets/frames.ts'
import { fixed }              from '../../../../lib/widgets/numbers.ts'
import { Chip }               from '../../kit/chip.tsx'
import { SearchMarks }        from './marks.tsx'

/**
 * The classes the screen takes in each state, a dead copy's dimmed most and a
 * live copy that lost dimmed less.
 */
const FADES = { '': null, dead: 'opacity-30', lost: 'opacity-60', moved: null, win: null } as const

/**
 * One copy of the game: its screen, the cross over it once its rollout ends
 * dead, the badge of the flag its rollout set, and beneath it the button it
 * holds with its uncertainty once the rollout ends. The screen glides through
 * each press, and the copy dims where the key names a mark it does not carry.
 */
export const SearchCopy = defineComponent({
  name: 'SearchCopy',

  props: {
    dim    : { required: true, type: Boolean },
    images : { required: true, type: Object as PropType<RoomImages> },
    label  : { required: true, type: String },
    shown  : { required: true, type: Object as PropType<Shown> }
  },

  setup: props => {
    const canvas          = ref<HTMLCanvasElement>()
    const screen          = new CopyScreen(props.images)
    const { paint, wake } = useCanvasLoop(canvas, screen)

    watch(() => props.shown, shown => {
      screen.show(shown)
      paint()
      wake()
    }, { immediate: true })
    onMounted(() => props.images.whenReady(paint))

    return () => {
      const { copy, state, term, uncertainty } = props.shown
      return (
        <figure
          class={[
            'search-copy m-0 grid min-w-0 gap-2 motion-safe:transition-opacity',
            props.dim ? 'opacity-45' : null
          ]}
          data-state={state}
        >
          <div class="search-glass relative overflow-hidden rounded-1 border-hairline border-rule">
            <canvas
              aria-label={props.label}
              class={['pixelated block h-auto w-full motion-safe:transition-opacity', FADES[state]]}
              height={SCREEN.height}
              ref={canvas}
              role="img"
              width={SCREEN.width}
            />
            <SearchMarks dead={state === 'dead'} term={term} />
          </div>
          <Chip
            class="w-full"
            mark={padMark(copy.held)}
            name={pressName(copy.held)}
            value={uncertainty === null ? '–' : fixed(uncertainty, 2)}
          />
        </figure>
      )
    }
  }
})
