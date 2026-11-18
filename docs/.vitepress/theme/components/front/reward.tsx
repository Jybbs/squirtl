import { defineComponent, ref, useId } from 'vue'

import { figuresAt, showingOf }   from '../../../lib/front/reward.ts'
import { useClimb }               from '../../../lib/front/reward/climb.ts'
import { useEpisode }             from '../../../lib/front/reward/screen.ts'
import { SCREEN }                 from '../../../lib/game/screen.ts'
import { type Parts, Slider }     from '../kit/slider.tsx'
import { GAME_VIEW }              from '../kit/widget.ts'
import { drawClimb }              from './reward/climb.tsx'
import { RewardKey, drawFigures } from './reward/figures.tsx'

/**
 * The classes laying out each part of the widget beside the ones every view of
 * the game takes: the climb's box, which stretches to the screen's height once
 * the two sit side by side, the plot holding the figures and the climb, and the
 * screen.
 */
const LAYOUT = {
  box    : 'relative h-reward-climb @lg:h-auto',
  plot   : 'relative grid min-w-0 @max-lg:mb-6',
  screen : 'self-start'
}

/**
 * The classes laying the climb's slider over its box: the control inset to the
 * ends of the course, and the thumb filling the box from its top left, where a
 * box positioned absolutely sits while its insets stay unset.
 */
const CLIMB: Parts = {
  control : 'absolute right-6 left-7 h-full select-none',
  root    : 'absolute inset-0',
  thumb   : 'absolute size-full'
}

/**
 * The reward the front page tells first: Blue playing one episode of the first
 * rooms on the game's screen beside the return's climb across it, the climb's
 * top and floor on the screen's top and bottom edges and the figures in its
 * upper corner, every figure a chip, from the widget's 60rem, and below that
 * width the screen, the figures, and the climb stacked in that order. The climb
 * is the widget's slider, a press or a drag along it or the arrow keys showing
 * the screen and the figures at a step, and a mouse resting on it holding the
 * episode.
 */
export const StoryReward = defineComponent({
  name  : 'StoryReward',
  setup : () => {
    const box      = ref<HTMLElement>()
    const canvas   = ref<HTMLCanvasElement>()
    const clip     = useId()
    const root     = ref<HTMLElement>()
    const showing  = showingOf()
    const plot     = useClimb(box, showing.trace)
    const playback = useEpisode(canvas, root, showing)

    return () => (
      <div class="@container" ref={root}>
        <div class="reward-pair grid gap-x-6 gap-y-5 @lg:mb-6">
          <canvas
            aria-label="The game screen, Blue playing one episode of the first rooms"
            class={[GAME_VIEW, LAYOUT.screen]}
            height={SCREEN.height}
            ref={canvas}
            role="img"
            width={SCREEN.width}
          />
          <div class={LAYOUT.plot}>
            {drawFigures(figuresAt(showing.trace, playback.at.value))}
            <div class={LAYOUT.box} ref={box}>
              {plot.value ? drawClimb(plot.value, playback.at.value, clip) : null}
              <Slider parts={CLIMB} scrub={playback.scrub} />
            </div>
          </div>
        </div>
        <RewardKey />
      </div>
    )
  }
})
