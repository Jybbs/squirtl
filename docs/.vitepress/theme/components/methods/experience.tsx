import { defineComponent, ref } from 'vue'

import * as experience           from '../../../lib/methods/experience.ts'
import { useExperiencePlayback } from '../../../lib/methods/experience/playback.ts'
import { count }                 from '../../../lib/widgets/numbers.ts'
import { Chip }                  from '../kit/chip.tsx'
import { Key }                   from '../kit/key.tsx'
import { COVER, LABEL }          from '../kit/widget.ts'
import { drawLine, drawTicks }   from './experience/line.tsx'
import { drawStrip }             from './experience/strip.tsx'

/**
 * The words the widget sets, the label over the update, the name a screen
 * reader reads for the drawing and for the slider, and the key's one entry.
 */
const WORDS = {
  drawing : `Each update’s ${experience.MEMORY.batch} arcs easing one after another, newest first, from the last update’s steps to this one’s, each shown window sliding with its arc`,
  slider  : 'The deep Q-network’s updates, held at the update it names',
  update  : 'This update'
}

/**
 * The key's one entry, an arc from the update to a step it reads.
 */
const KEY = [{
  mark : '<svg viewBox="0 0 16 16"><path d="M2 13 Q8 1 14 13" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>',
  name : 'A step read',
  note : 'An arc from this update to a step it reads, easing to the next update’s step as the clock moves',
  role : 'agent'
}] as const

/**
 * The deep Q-network reading replay memory: each update as a dot at the right
 * end of a line of time running back to the oldest step replay memory holds,
 * an arc from it to each step it reads, and a window under every fourth arc
 * showing the step it lands on. Each update moves its arcs to the steps it
 * reads one after another, newest first, each arc easing on the identity's
 * curve from where the last update's landed and its window sliding with it. The
 * chips read the median age of the steps read, the newest, and the oldest, and
 * a press or a drag along the drawing or the arrow keys hold it at an update.
 */
export const MethodsExperience = defineComponent({
  name  : 'MethodsExperience',
  setup : () => {
    const box     = ref<HTMLElement>()
    const { ages, arcs, scrub, windows } = useExperiencePlayback(box, WORDS.slider)

    return () => {
      const figures = experience.figuresOf(ages.value)

      return (
        <div class="@container grid gap-3">
          <div {...scrub.root.value} class="relative grid gap-1" ref={box}>
            <p aria-hidden="true" class={[LABEL, 'm-0 justify-self-end']}>{WORDS.update}</p>
            {drawLine(arcs.map(arc => arc.value), WORDS.drawing)}
            {drawTicks()}
            {drawStrip(windows)}
            <div {...scrub.control.value} class={COVER.control} />
            <div {...scrub.thumb.value} class={COVER.thumb} />
          </div>
          <div class="experience-chips grid gap-2">
            <Chip class="w-full" name="Median age" note="steps" value={count(figures.median)} />
            <Chip class="w-full" name="Newest read" note="steps" value={count(figures.newest)} />
            <Chip class="w-full" name="Oldest read" note="steps" value={count(figures.oldest)} />
          </div>
          <Key entries={KEY} />
        </div>
      )
    }
  }
})
