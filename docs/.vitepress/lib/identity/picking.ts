import { computed, ref } from 'vue'

import { useChoice, usePick }                                       from '../widgets/choice.ts'
import { NAMED, type Picked, STEPS, hueOfToken, namedOf, shownOf } from './palette.ts'

/**
 * Holds the color a reader picks among the bands and the step of its hue's
 * ramp, the step cleared whenever another color is picked.
 *
 * Returns:
 *   The bands and the steps as groups of options, the color picked, its hue,
 *   and what the card shows.
 */
export function usePalette() {
  const at    = ref(NAMED[0]!.token)
  const step  = ref<Picked | null>(null)
  const bands = useChoice(NAMED.map(each => each.token), () => { step.value = null }, at)
  const color = computed(() => namedOf(at.value))

  return {
    bands : bands,
    color : color,
    hue   : computed(() => hueOfToken(at.value)),
    shown : computed(() => shownOf(color.value, step.value)),
    steps : usePick(STEPS, step)
  }
}
