import { type MaybeElementRef, useElementVisibility, useTimeoutFn } from '@vueuse/core'
import { type MaybeRefOrGetter, watch }                             from 'vue'

import { useMotion } from './motion.ts'

/**
 * A running autoplay, which a reader's pointer or keys hold and release.
 */
export interface Autoplay {
  hold : (reason: Reason, on: boolean) => void
}

/**
 * What an autoplay steps through, each beat calling `tick` until `done` reports
 * the run ended, then calling `restart` after `rest` where a run repeats, and
 * calling `finish` once at once where motion is off.
 */
export interface Ticking {
  beat     : MaybeRefOrGetter<number>
  done     : () => boolean
  finish   : () => void
  tick     : () => void
  rest?    : number
  restart? : () => void
}

/**
 * A reason a widget's autoplay holds, a pointer resting on its drawing or the
 * keys on its control.
 */
type Reason = 'keys' | 'pointer'

/**
 * How long a run that repeats rests on its end before it starts again, in
 * milliseconds, where its `Ticking` names no rest of its own.
 */
const REST = 3200

/**
 * The share of a widget that shows before its autoplay starts.
 */
const SHOWING = 0.2

/**
 * Steps `ticking` on a timer while `target` shows on screen and motion plays,
 * holding while any reason stands and, where the reader asks for reduced
 * motion, leaving the widget where the reader left it once the last reason
 * ends, and ends every timer when the widget unmounts.
 */
export function useAutoplay(target: MaybeElementRef, ticking: Ticking): Autoplay {
  const animate = useMotion()
  const holding = new Set<Reason>()
  const visible = useElementVisibility(target, { threshold: SHOWING })

  const run = () => {
    stop()
    if (!animate.value) return ticking.finish()
    if (holding.size > 0 || !visible.value) return
    if (ticking.done()) {
      if (ticking.restart) rest.start()
      return
    }
    ticking.tick()
    beat.start()
  }

  const again = () => {
    ticking.restart!()
    run()
  }

  const beat = useTimeoutFn(run, ticking.beat, { immediate: false })
  const rest = useTimeoutFn(again, ticking.rest ?? REST, { immediate: false })

  const stop = () => {
    beat.stop()
    rest.stop()
  }

  watch([visible, animate], run, { flush: 'sync' })

  return {
    hold: (reason, on) => {
      if (on) holding.add(reason)
      else holding.delete(reason)
      if (holding.size > 0) stop()
      else if (animate.value) run()
    }
  }
}
