import { type MaybeElementRef }            from '@vueuse/core'
import { type ComputedRef, computed, ref } from 'vue'

import { REST }                 from '../../widgets/autoplay.ts'
import { useFrameLoop }         from '../../widgets/frames.ts'
import { type Scrub, useScrub } from '../../widgets/scrub.ts'
import { LAST }                 from '../search.ts'
import * as moments             from './moments.ts'

/**
 * The search as the widget plays it: the slider's position, the copies as
 * they show, the figures over them, and the slider.
 */
export interface SearchPlayback {
  along   : ComputedRef<string>
  copies  : ComputedRef<moments.Shown[][]>
  figures : ComputedRef<moments.Figures>
  scrub   : Scrub
}

/**
 * Plays the search an iteration at a beat while the widget at `target` shows,
 * each beat playing the rollouts press by press, marking each group's winner,
 * and moving every other copy to it, then resting on the demonstration and
 * starting again from the first iteration. The slider holds it at the
 * iteration it names with each winner marked, and under reduced motion it rests
 * on the demonstration.
 */
export function useSearchPlayback(target: MaybeElementRef, label: string): SearchPlayback {
  const at      = ref(LAST)
  const t       = ref(moments.ITERATION)
  const moment  = computed(() => moments.momentOf(t.value))
  const along   = computed(() => `${100 * at.value / LAST}%`)
  const copies  = computed(() => moments.shownOf(at.value, moment.value))
  const figures = computed(() => moments.figuresOf(at.value, moment.value))

  const wake = useFrameLoop(target, elapsed => {
    t.value += elapsed
    return t.value < moments.ITERATION
  })

  const seek = (n: number) => {
    at.value = n
    t.value  = moments.ROLLING
  }

  const scrub = useScrub(target, {
    beat   : () => at.value === LAST ? REST : moments.ITERATION,
    done   : () => false,
    finish : () => seek(LAST),
    tick   : () => {
      at.value = (at.value + 1) % (LAST + 1)
      t.value  = 0
      wake()
    }
  }, { at, count: LAST + 1, describe: moments.describe, label, seek })

  return { along, copies, figures, scrub }
}
