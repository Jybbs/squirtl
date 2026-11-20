import { type MaybeElementRef, useElementVisibility, useTimeoutFn } from '@vueuse/core'
import { type MaybeRefOrGetter, onMounted, watch }                  from 'vue'

import { useMotion } from './motion.ts'

/**
 * A running autoplay, which a reader's pointer or keys hold and release, and
 * which a reader's change to what it plays starts over.
 */
export interface Autoplay {
  hold   : (reason: Reason, on: boolean) => void
  replay : () => void
}

/**
 * What an autoplay steps through, each beat calling `tick` until `done` reports
 * the run ended, then calling `restart` after `rest` where a run repeats, and
 * calling `finish` in its place where motion is off.
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
 * The ticking of a widget that never plays on its own, its one run already
 * done.
 */
export const IDLE: Ticking = { beat: 0, done: () => true, finish: () => {}, tick: () => {} }

/**
 * A reason a widget's autoplay holds, a pointer resting on its drawing or the
 * keys on its control.
 */
type Reason = 'keys' | 'pointer'

/**
 * How long a run that repeats rests on its end before it starts again, in
 * milliseconds, where its `Ticking` names no rest of its own.
 */
export const REST = 3200

/**
 * The share of a widget that shows before its autoplay starts.
 */
const SHOWING = 0.2

/**
 * Steps `ticking` on a timer while `target` shows on screen and motion plays,
 * holding while any reason stands, and ends every timer when the widget
 * unmounts. Where the reader asks for reduced motion, it calls `finish` once
 * the widget mounts or the preference takes hold, and again on each replay, so
 * a position the reader picks survives the widget leaving the screen and
 * coming back.
 */
export function useAutoplay(target: MaybeElementRef, ticking: Ticking): Autoplay {
  const animate = useMotion()
  const holding = new Set<Reason>()
  const visible = useElementVisibility(target, { threshold: SHOWING })

  const run = () => {
    stop()
    if (!animate.value || holding.size > 0 || !visible.value) return
    if (ticking.done()) {
      if (ticking.restart) rest.start()
      return
    }
    ticking.tick()
    beat.start()
  }

  const settle = () => animate.value ? run() : ticking.finish()

  const again = () => {
    ticking.restart?.()
    settle()
  }

  const beat = useTimeoutFn(run, ticking.beat, { immediate: false })
  const rest = useTimeoutFn(again, ticking.rest ?? REST, { immediate: false })

  const stop = () => {
    beat.stop()
    rest.stop()
  }

  watch(visible, run, { flush: 'sync' })
  watch(animate, settle, { flush: 'sync' })
  onMounted(settle)

  return {
    hold: (reason, on) => {
      if (on) holding.add(reason)
      else holding.delete(reason)
      run()
    },
    replay: again
  }
}
