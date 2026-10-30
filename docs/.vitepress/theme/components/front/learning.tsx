import { defineComponent, ref, useId } from 'vue'

import { sceneLabel, walksOf }  from '../../../lib/front/learning.ts'
import * as play                from '../../../lib/front/learning/play.ts'
import { Walks }                from '../../../lib/front/learning/walks.ts'
import { GAME_VIEW }            from '../kit/widget.ts'
import { WalkButtons, WalkKey } from './learning/keys.tsx'
import { WalkStrip }            from './learning/strip.tsx'

/**
 * The front page's widget for learning the walk: one still view of Pallet
 * Town's north half, where Blue's walks from his door after more and more
 * episodes of training set off together on one clock of presses, each in its
 * own hue, over a button for each walk, a strip of their presses, and the key
 * to its marks.
 *
 * It plays once it scrolls into view and loops through pret/pokered's
 * transition into a wild battle. A mouse resting on the strip holds the clock
 * and picks out the Blue of the walk it points at, a press or a drag along the
 * strip or the arrow keys once it has focus move the clock, and each walk's
 * button picks out its Blue while pointed at or pressed. Under reduced motion
 * it shows the walks' ends at once.
 */
export const StoryLearning = defineComponent({
  name  : 'StoryLearning',
  setup : () => {
    const id       = useId()
    const moments  = walksOf()
    const walks    = new Walks(moments)
    const { hues } = walks
    const label    = sceneLabel(moments)
    const canvas   = ref<HTMLCanvasElement>()
    const root     = ref<HTMLElement>()
    const painting = play.useTownCanvas(canvas, walks)
    const playback = play.usePlayback(painting, root, walks)
    const picking  = play.usePicking(painting, walks)

    return () => (
      <div class="@container grid gap-3" ref={root}>
        <canvas
          aria-label={label}
          class={[GAME_VIEW, 'mb-2']}
          height={walks.view.height}
          ref={canvas}
          role="img"
          width={walks.view.width}
        />
        <WalkButtons
          at={playback.at.value}
          hues={hues}
          moments={moments}
          onHover={picking.hover}
          onPin={picking.pin}
          picked={picking.picked.value}
          pinned={picking.pinned.value}
        />
        <WalkStrip
          at={playback.at.value}
          hues={hues}
          id={id}
          moments={moments}
          onPoint={picking.hover}
          picked={picking.picked.value}
          scrub={playback.scrub}
        />
        <WalkKey hue={hues.at(-1)!} id={id} />
      </div>
    )
  }
})
