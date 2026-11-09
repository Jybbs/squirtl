import { type ComputedRef, type Ref, computed, ref } from 'vue'

import { useMotion }                from '../../widgets/motion.ts'
import { count }                    from '../../widgets/numbers.ts'
import { type Scrub, useScrub }     from '../../widgets/scrub.ts'
import * as experience              from '../experience.ts'
import { useArcs }                  from './arcs.ts'
import { type Windows, useWindows } from './windows.ts'

/**
 * Replay memory as the widget plays it: the ages of the steps the update reads,
 * each arc easing toward its step, the windows under every fourth arc, and the
 * slider over the updates.
 */
export interface ExperiencePlayback {
  ages    : ComputedRef<readonly number[]>
  arcs    : Ref<number>[]
  scrub   : Scrub
  windows : Windows
}

/**
 * Plays an update a beat while the widget at `box` shows, moving each arc and
 * window to the steps the update reads, and holds it at the update the slider
 * names.
 */
export function useExperiencePlayback(box: Ref<HTMLElement | undefined>, label: string): ExperiencePlayback {
  const at     = ref(0)
  const motion = useMotion()
  const ages   = computed(() => experience.agesOf(at.value))
  const scrub  = useScrub(box, {
    beat   : experience.BEAT,
    done   : () => false,
    finish : () => {},
    tick   : () => { at.value = (at.value + 1) % experience.UPDATES }
  }, {
    at,
    count    : experience.UPDATES,
    describe : update => `Update ${count(update + 1)}`,
    label,
    seek     : update => { at.value = update }
  })

  return { ages, arcs: useArcs(ages, computed(() => !motion.value)), scrub, windows: useWindows(ages, motion) }
}
