import { defineComponent, ref } from 'vue'

import { SQUARE }                      from '../../../lib/game/screen.ts'
import * as reach                      from '../../../lib/methods/reach.ts'
import { KEY }                         from '../../../lib/methods/reach/key.ts'
import { CROP }                        from '../../../lib/methods/reach/paint.ts'
import { useReachPlayback }            from '../../../lib/methods/reach/playback.ts'
import { GROUPS, SCREENS, useScreens } from '../../../lib/methods/reach/screens.ts'
import { Key }                         from '../kit/key.tsx'
import { COVER, DETAIL, LABEL }        from '../kit/widget.ts'

/**
 * The words the widget sets.
 */
const WORDS = { slider: 'Training, held after the pass it names' }

/**
 * The reach of each learner's update: Blue walking up Pallet Town's tenth
 * column to the north edge, where Oak calls him back and the walk pays, on a
 * screen for the deep Q-network's online network and its copy, PQN's one
 * network, and PPO's odds, the Game Boy's pad on every square of the walk with
 * each arm filled as far as its learner's value of that press or, for PPO, its
 * odds. Training plays a pass at a time, the values landing as Oak calls Blue
 * back, and a press or a drag along the screens or the arrow keys hold it after
 * a pass.
 */
export const MethodsReach = defineComponent({
  name  : 'MethodsReach',
  setup : () => {
    const box                                    = ref<HTMLElement>()
    const canvases                               = ref<HTMLCanvasElement[]>([])
    const { at, copied, landed, moment, scrub } = useReachPlayback(box, WORDS.slider)
    useScreens(canvases, moment, landed, copied)

    return () => (
      <div class="@container grid gap-3">
        <div {...scrub.root.value} class="relative" ref={box}>
          <div class="reach-screens grid gap-x-2 gap-y-2">
            {GROUPS.map(({ group, span }) => (
              <p class={[LABEL, 'm-0 border-b-hairline border-rule pb-1 whitespace-nowrap text-ink']} style={{ gridColumn: `span ${span}` }}>{group}</p>
            ))}
            {SCREENS.map((screen, n) => (
              <figure class="m-0 grid min-w-0 gap-1.5">
                <canvas
                  aria-label={`The walk up to the north edge with the Game Boy’s pad on every square, each arm filled by ${screen.says}`}
                  class="pixelated block h-auto w-full rounded-1 border-hairline border-rule"
                  height={CROP.h * SQUARE * CROP.scale}
                  ref={(canvas: unknown) => { if (canvas) canvases.value[n] = canvas as HTMLCanvasElement }}
                  role="img"
                  width={CROP.w * SQUARE * CROP.scale}
                />
                <figcaption class={[LABEL, 'text-center']}>{screen.name}</figcaption>
              </figure>
            ))}
          </div>
          <div {...scrub.control.value} class={COVER.control} />
          <div {...scrub.thumb.value} class={COVER.thumb} />
        </div>
        <span class={[DETAIL, 'reach-status text-ink']}>{at.value ? `Pass ${at.value} of ${reach.PASSES}` : 'Before training'}</span>
        <Key entries={KEY} />
      </div>
    )
  }
})
