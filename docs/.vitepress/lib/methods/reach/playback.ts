import { useTransition } from '@vueuse/core'
import { type ComputedRef, type Ref, type WritableComputedRef, computed, ref } from 'vue'

import { FRAME }                from '../../game/screen.ts'
import { IDENTITY }             from '../../identity/identity.ts'
import { useMotion }            from '../../widgets/motion.ts'
import { type Scrub, useScrub } from '../../widgets/scrub.ts'
import * as reach               from '../reach.ts'

/**
 * Training as the widget plays it: the pass it stands after, the moment of the
 * line the clock reaches, how far the values and the copy have landed, and the
 * slider over the passes.
 */
export interface ReachPlayback {
  at     : WritableComputedRef<number>
  copied : Ref<number>
  landed : Ref<number>
  moment : ComputedRef<reach.Moment>
  scrub  : Scrub
}

/**
 * Plays training on the Game Boy's frame clock while the widget at `box`
 * shows, easing the values and the copy onto each pass on the identity's curve,
 * at once under reduced motion, and holds it after the pass the slider names.
 */
export function useReachPlayback(box: Ref<HTMLElement | undefined>, label: string): ReachPlayback {
  const clock  = ref(0)
  const motion = useMotion()
  const still  = computed(() => !motion.value)
  const moment = computed(() => reach.momentAt(clock.value))
  const easing = [...IDENTITY.motion.curve] as [number, number, number, number]
  const landed = useTransition(() => moment.value.landed, { disabled: still, duration: reach.FRAMES.settle * FRAME, easing })
  const copied = useTransition(() => moment.value.pass, { disabled: still, duration: reach.FRAMES.copy * FRAME, easing })

  const at = computed({
    get : () => moment.value.pass,
    set : pass => { clock.value = reach.clockOf(pass) }
  })

  const scrub = useScrub(box, {
    beat   : FRAME,
    done   : () => false,
    finish : () => { at.value = reach.PASSES },
    tick   : () => { clock.value = (clock.value + 1) % reach.LINE.total }
  }, {
    at,
    count    : reach.PASSES + 1,
    describe : pass => reach.passName(pass),
    label,
    seek     : pass => { at.value = pass }
  })

  return { at, copied, landed, moment, scrub }
}
