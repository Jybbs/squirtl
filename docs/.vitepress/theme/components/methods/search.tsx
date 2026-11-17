import { computed, defineComponent, ref } from 'vue'

import { RoomImages }        from '../../../lib/game/images.ts'
import { KEY }               from '../../../lib/methods/search/key.ts'
import type { Figures }      from '../../../lib/methods/search/moments.ts'
import { useSearchPlayback } from '../../../lib/methods/search/playback.ts'
import { count }             from '../../../lib/widgets/numbers.ts'
import { Chip }              from '../kit/chip.tsx'
import { Key }               from '../kit/key.tsx'
import { LIST, SCRUB_PARTS } from '../kit/widget.ts'
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
 * Draws the chips over the copies: the iteration, or the demonstration's
 * length, the tree's nodes and saved states, and the presses spent.
 */
function chipsOf(figures: Figures) {
  return (
    <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
      <Chip
        class="w-full"
        name={figures.demonstration ? 'Demonstration' : 'Iteration'}
        value={figures.iteration}
      />
      <Chip class="w-full" name="Nodes" value={count(figures.nodes)} />
      <Chip class="w-full" name="Saved states" value={count(figures.saved)} />
      <Chip class="w-full" name="Presses spent" value={count(figures.spent)} />
    </div>
  )
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
    const box                               = ref<HTMLElement>()
    const hovered                           = ref<number | null>(null)
    const pressed                           = ref<number | null>(null)
    const lit                               = computed(() => hovered.value ?? pressed.value)
    const images                            = new RoomImages()
    const { along, copies, figures, scrub } = useSearchPlayback(box, WORDS.slider)

    return () => (
      <div class="grid gap-4" ref={box}>
        {chipsOf(figures.value)}
        <ol aria-label={WORDS.groups} class={[LIST, 'grid touch-pan-y gap-4']}>
          {copies.value.map((group, g) => (
            <SearchGroup copies={group} images={images} lit={lit.value} n={g + 1} />
          ))}
        </ol>
        <div {...scrub.root.value} class="relative">
          <div {...scrub.control.value} class={[SCRUB_PARTS.control, 'relative h-6 select-none']}>
            <span class="absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-rule" />
            <span
              class="absolute top-1/2 left-0 h-1 -translate-y-1/2 rounded-full bg-denim-mark"
              style={{ width: along.value }}
            />
          </div>
          <div
            {...scrub.thumb.value}
            class={[
              SCRUB_PARTS.thumb,
              'absolute top-1/2 size-4 -translate-1/2 rounded-full border-ring border-lift bg-denim-mark'
            ]}
            style={{ left: along.value }}
          />
        </div>
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
