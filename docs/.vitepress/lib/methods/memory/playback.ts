import { type MaybeElementRef }      from '@vueuse/core'
import { type Ref, ref, shallowRef } from 'vue'

import { useFrameLoop }               from '../../widgets/frames.ts'
import { type Scrub, useScrub }       from '../../widgets/scrub.ts'
import { LAST, describe }             from '../memory.ts'
import { FRAME_MS, type Frame, PLAY } from './play.ts'

/**
 * The episode as the widget plays it, the step it stands at, the frame it
 * shows, and the slider over its steps.
 */
export interface MemoryPlayback {
  at    : Ref<number>
  frame : Ref<Frame>
  scrub : Scrub
}

/**
 * The milliseconds the episode rests on its last step before it plays again
 * from the bedroom.
 */
const REST = 3600

/**
 * Plays the episode step by step while the widget at `target` shows, each step
 * frame by frame as the game draws it, and holds it at the step the slider
 * names, showing the frame that step ends on.
 */
export function useMemoryPlayback(target: MaybeElementRef, label: string): MemoryPlayback {
  const at    = ref(0)
  const frame = shallowRef<Frame>(PLAY.ends[0]!)
  let playing: readonly Frame[] = []
  let elapsed = 0

  const wake = useFrameLoop(target, dt => {
    elapsed += dt
    const f = Math.min(playing.length - 1, Math.floor(elapsed / FRAME_MS))
    if (f >= 0) frame.value = playing[f]!
    return f < playing.length - 1
  })

  const run = (n: number) => {
    at.value = n
    playing  = PLAY.steps[n]!
    elapsed  = 0
    wake()
  }

  const seek = (n: number) => {
    at.value    = n
    playing     = []
    frame.value = PLAY.ends[n]!
  }

  const scrub = useScrub(target, {
    beat    : () => PLAY.steps[Math.max(at.value, 0)]!.length * FRAME_MS,
    done    : () => at.value >= LAST,
    finish  : () => seek(LAST),
    rest    : REST,
    restart : () => { at.value = -1 },
    tick    : () => run(at.value + 1)
  }, { at, count: LAST + 1, describe, label, seek })

  return { at, frame, scrub }
}
