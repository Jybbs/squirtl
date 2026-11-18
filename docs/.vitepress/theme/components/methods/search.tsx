import { computed, defineComponent, ref } from 'vue'

import { RoomImages }        from '../../../lib/game/images.ts'
import { KEY }               from '../../../lib/methods/search/key.ts'
import { useSearchPlayback } from '../../../lib/methods/search/playback.ts'
import { Key }               from '../kit/key.tsx'
import { Slider }            from '../kit/slider.tsx'
import { LIST }              from '../kit/widget.ts'
import { drawFigures }       from './search/figures.tsx'
import { SearchGroup }       from './search/group.tsx'

/**
 * The words the widget sets.
 */
const WORDS = {
  groups : 'The two groups of copies of the game, each copy’s screen and the button it holds',
  slider : 'The search’s iterations, which hold the copies at the end of the iteration it names, and the '
         + 'demonstration after the last'
}

/**
 * Eight copies of the game in two groups of four: each copy's screen, the
 * button it holds through its rollout and its uncertainty beneath once the
 * rollout ends, a dead copy dimmed and crossed out, each group's winner
 * ringed, and every other copy then fading in on the winner's saved state.
 * The figures over the copies count the iteration, the presses spent, and the
 * tree's nodes and saved states, each group's reward chip the most its copies
 * hold, and the slider beneath holds the search at an iteration or at the
 * demonstration. Lighting an entry of the key dims every copy without its mark.
 */
export const MethodsSearch = defineComponent({
  name  : 'MethodsSearch',
  setup : () => {
    const box                            = ref<HTMLElement>()
    const hovered                        = ref<number | null>(null)
    const pressed                        = ref<number | null>(null)
    const lit                            = computed(() => hovered.value ?? pressed.value)
    const images                         = new RoomImages()
    const { at, copies, figures, scrub } = useSearchPlayback(box, WORDS.slider)

    return () => (
      <div class="grid gap-4" ref={box}>
        {drawFigures(figures.value)}
        <ol aria-label={WORDS.groups} class={[LIST, 'grid touch-pan-y gap-4']}>
          {copies.value.map((group, g) => (
            <SearchGroup copies={group} images={images} lit={lit.value} n={g + 1} />
          ))}
        </ol>
        <Slider at={at.value} scrub={scrub} />
        <Key
          entries={KEY}
          lit={lit.value}
          onHover={(n: number | null) => { hovered.value = n }}
          onPress={(n: number) => { pressed.value = pressed.value === n ? null : n }}
          pressable={true}
          pressed={pressed.value}
        />
      </div>
    )
  }
})
