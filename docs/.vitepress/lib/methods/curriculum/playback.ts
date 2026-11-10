import { type MaybeElementRef }                      from '@vueuse/core'
import { type ComputedRef, type Ref, computed, ref } from 'vue'

import { useFrameLoop }         from '../../widgets/frames.ts'
import { type Scrub, useScrub } from '../../widgets/scrub.ts'
import * as curriculum          from '../curriculum.ts'
import { type Lane, laneAt }    from './screens.ts'

/**
 * The run as the widget plays it: the batch it stands at, where each segment's
 * screen stands in it, and the slider over the batches.
 */
export interface CurriculumPlayback {
  at    : Ref<number>
  lanes : ComputedRef<Lane[]>
  scrub : Scrub
}

/**
 * Plays the run a batch at a beat while the widget at `target` shows, each
 * batch replaying the recording up to every segment's start before the agent
 * stands there, and starting again after the last. The slider holds it at the
 * batch it names, every screen at its start, and under reduced motion it rests
 * on the last batch.
 */
export function useCurriculumPlayback(target: MaybeElementRef, label: string): CurriculumPlayback {
  const last  = curriculum.BATCHES - 1
  const at    = ref(last)
  const t     = ref(Number.POSITIVE_INFINITY)
  const lanes = computed(() => curriculum.RUN[at.value]!.map(each => laneAt(each.start, t.value)))

  const wake = useFrameLoop(target, elapsed => {
    t.value += elapsed
    return t.value < curriculum.TIMING.replay
  })

  const seek = (b: number) => {
    at.value = b
    t.value  = Number.POSITIVE_INFINITY
  }

  const scrub = useScrub(target, {
    beat   : curriculum.TIMING.replay + curriculum.TIMING.rest,
    done   : () => false,
    finish : () => seek(last),
    tick   : () => {
      at.value = (at.value + 1) % curriculum.BATCHES
      t.value  = 0
      wake()
    }
  }, { at, count: curriculum.BATCHES, describe: curriculum.describe, label, seek })

  return { at, lanes, scrub }
}
