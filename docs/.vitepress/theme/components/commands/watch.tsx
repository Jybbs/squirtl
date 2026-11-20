import { defineComponent, ref } from 'vue'

import * as watching                          from '../../../lib/commands/watch.ts'
import { useWatchPlayback }                   from '../../../lib/commands/watch/playback.ts'
import { useWatchScreen }                     from '../../../lib/commands/watch/screen.ts'
import { SCREEN }                             from '../../../lib/game/screen.ts'
import { count }                              from '../../../lib/widgets/numbers.ts'
import { OVER, type Parts, Slider }           from '../kit/slider.tsx'
import { DETAIL, GAME_VIEW, LABEL }           from '../kit/widget.ts'
import { drawAfter, drawBefore, drawPresses } from './watch/parts.tsx'

/**
 * The words the widget sets.
 */
const WORDS = {
  presses : 'The presses',
  screen  : 'PyBoy’s window replaying the episode',
  slider  : 'The recording’s presses, a press on one holding the playback there'
}

/**
 * The classes of the slider over the recording's presses: the band of bytes as
 * its control, and the thumb laid over the band.
 */
const PRESSES: Parts = {
  control : 'watch-band grid select-none gap-1',
  root    : 'relative',
  thumb   : OVER.thumb
}

/**
 * `squirtl watch` playing an episode back: PyBoy's window replaying the
 * recording at sixty steps a second, the state the intro leaves checked against
 * the run's digest before a press plays, the return the playback reaches checked
 * against the recorded one once the last press has played, and the recording's
 * presses in a band across the foot. A press on a byte or the arrow keys hold
 * the playback there.
 */
export const CommandsWatch = defineComponent({
  name  : 'CommandsWatch',
  setup : () => {
    const box                      = ref<HTMLElement>()
    const canvas                   = ref<HTMLCanvasElement>()
    const { band, scrub, step, t } = useWatchPlayback(box, WORDS.slider)
    useWatchScreen(canvas, t, step)

    return () => (
      <div class="@container">
        <div class="watch grid gap-4">
          <div class="watch-window grid self-start overflow-hidden rounded-2 border-hairline border-rule bg-lift" style={{ opacity: watching.windowAt(t.value) }}>
            <p class={[LABEL, 'm-0 border-b-hairline border-rule py-2 text-center']}>PyBoy</p>
            <canvas aria-label={WORDS.screen} class={[GAME_VIEW, 'rounded-none border-0']} height={SCREEN.height} ref={canvas} role="img" width={SCREEN.width} />
          </div>
          {drawBefore(t.value)}
          {drawAfter(t.value, step.value)}
          <div class="watch-presses grid min-w-0 gap-2">
            <p class="m-0 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-2">
              <span class={LABEL}>{WORDS.presses}</span>
              <span class={DETAIL}>{`${count(watching.LAST)} bytes · timer_div ${watching.RUN.timerDiv}`}</span>
            </p>
            <div ref={box}>
              <Slider band={band} parts={PRESSES} scrub={scrub}>{drawPresses(step.value)}</Slider>
            </div>
          </div>
        </div>
      </div>
    )
  }
})
