import { defineComponent, ref, useId } from 'vue'

import { useRace, useRaceClock } from '../../../lib/front/race/chart.ts'
import * as race                 from '../../../lib/front/race.ts'
import { Key }                   from '../kit/key.tsx'
import { OVER, Slider }          from '../kit/slider.tsx'
import { drawRace }              from './race/chart.tsx'

/**
 * The words the widget sets, the key's label and the heads over its figures.
 */
const WORDS = {
  heads : ['Reached it', 'Steps to it'] as const,
  key   : 'Episodes that have reached the starter'
}

/**
 * The race against random presses: the agent's stand-in and random presses each
 * playing the evaluation's episodes under the same seeds, the chart rising with
 * the episodes that have reached the starter on a clock of steps along a log
 * scale, and the key counting them. The clock runs on its own once the chart
 * shows, and the chart is its slider, a press or a drag along it or the arrow
 * keys setting the step, and a mouse resting on it holding the clock.
 */
export const StoryRace = defineComponent({
  name  : 'StoryRace',
  setup : () => {
    const box   = ref<HTMLElement>()
    const clip  = useId()
    const drawn = race.raceOf()
    const root  = ref<HTMLElement>()
    const plot  = useRace(box, drawn)
    const clock = useRaceClock(drawn, root)

    return () => (
      <div class="@container grid gap-3" ref={root}>
        <Key
          entries={race.scoresOf(race.clockAt(clock.at.value), drawn)}
          heads={WORDS.heads}
          label={WORDS.key}
        />
        <div class="relative h-race-plot" ref={box}>
          {drawRace(plot.value, clip, clock.at.value)}
          <Slider parts={OVER} scrub={clock.scrub} />
        </div>
      </div>
    )
  }
})
