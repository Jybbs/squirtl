import { computed, defineComponent, ref } from 'vue'

import type * as rooms         from '../../../lib/game/rooms.ts'
import { LAST }                from '../../../lib/methods/memory.ts'
import { KEY }                 from '../../../lib/methods/memory/marks.ts'
import { useMemoryPlayback }   from '../../../lib/methods/memory/playback.ts'
import { Key }                 from '../kit/key.tsx'
import { DETAIL, SCRUB_PARTS } from '../kit/widget.ts'
import { MemoryBytes }         from './memory/bytes.tsx'
import { MemorySays }          from './memory/says.tsx'
import { MemoryStage }         from './memory/stage.tsx'

/**
 * The words the widget sets.
 */
const WORDS = {
  hint   : 'Point at a square to read the bytes it would hold and whether the episode has reached it while the episode plays on. The slider beneath the map, or the arrow keys once it has focus, hold the episode at a step.',
  slider : 'The episode’s steps, which hold the bytes at the step it names'
}

/**
 * The bytes the reward reads after every step, drawn on the map Blue stands
 * on as he walks it the way the game moves and draws him: a pixel dot on each
 * square reached, popping in large and settling small and lighter the more
 * steps have passed since, the newest ringed, a dashed site where the game
 * sets each flag, filled and sending one ring out as it is set, and the bytes'
 * square gliding to each square the bytes name with its numbers at the map's
 * edges. The bytes and the key stand beside the map, and the sentence for each
 * step runs beneath both. The slider beneath the map holds the episode at a
 * step, and a pointer resting on a square reads its bytes while the episode
 * plays on.
 */
export const MethodsMemory = defineComponent({
  name  : 'MethodsMemory',
  setup : () => {
    const box                  = ref<HTMLElement>()
    const hovered              = ref<number | null>(null)
    const pressed              = ref<number | null>(null)
    const lit                  = computed(() => hovered.value ?? pressed.value)
    const pointed              = ref<rooms.Square | null>(null)
    const { at, frame, scrub } = useMemoryPlayback(box, WORDS.slider)
    const square               = computed(() => pointed.value ?? frame.value.square)

    return () => (
      <div class="@container" ref={box}>
        <div class="memory grid items-start gap-x-5 gap-y-4">
          <div class="memory-plate grid min-w-0 gap-3">
            <MemoryStage frame={frame.value} lit={lit.value} onPoint={(next: rooms.Square | null) => { pointed.value = next }} pointed={pointed.value} />
            <div {...scrub.root.value} class="memory-under relative">
              <div {...scrub.control.value} class={[SCRUB_PARTS.control, 'relative h-6 select-none']}>
                <span class="absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-rule" />
                <span class="absolute top-1/2 left-0 h-1 -translate-y-1/2 rounded-full bg-denim-mark" style={{ width: `${100 * Math.max(at.value, 0) / LAST}%` }} />
              </div>
              <div {...scrub.thumb.value} class={[SCRUB_PARTS.thumb, 'absolute top-1/2 size-4 -translate-1/2 rounded-full border-ring border-lift bg-denim-mark']} style={{ left: `${100 * Math.max(at.value, 0) / LAST}%` }} />
            </div>
          </div>
          <div class="memory-side grid min-w-0 content-start gap-4">
            <MemoryBytes frame={frame.value} square={square.value} />
            <Key entries={KEY} lit={lit.value} onHover={(n: number | null) => { hovered.value = n }} onPress={(n: number) => { pressed.value = pressed.value === n ? null : n }} pressable={true} pressed={pressed.value} />
          </div>
          <MemorySays frame={frame.value} pointed={pointed.value} />
          <p class={[DETAIL, 'memory-hint m-0']}>{WORDS.hint}</p>
        </div>
      </div>
    )
  }
})
