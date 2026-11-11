import { type PropType, defineComponent } from 'vue'

import { termMark }            from '../../../../lib/game/actors.ts'
import type { RoomImages }     from '../../../../lib/game/images.ts'
import { type Segment, along } from '../../../../lib/methods/curriculum.ts'
import { useLane }             from '../../../../lib/methods/curriculum/lanes.ts'
import { LENS, type Lane }     from '../../../../lib/methods/curriculum/screens.ts'
import { LABEL }               from '../../kit/widget.ts'

/**
 * One segment's lane: the goal's mark and words, then a track from the bedroom
 * to the goal with the screen standing at the episode's start, gray behind it
 * as far as the recording carries Blue and Denim ahead of it to the goal, and
 * how far before the goal the episode starts beside it. The screen, the two
 * stretches, and the words glide to each new start, and the gray wipes off the
 * screen toward the bedroom as the agent takes over.
 */
export const CurriculumLane = defineComponent({
  name: 'CurriculumLane',

  props: {
    far     : { required: true, type: String },
    images  : { required: true, type: Object as PropType<RoomImages> },
    lane    : { required: true, type: Object as PropType<Lane> },
    segment : { required: true, type: Object as PropType<Segment> },
    start   : { required: true, type: Number }
  },

  setup: props => {
    const { after, before, canvas, far, screen, track } = useLane(props)

    return () => (
      <li class="curriculum-lane col-span-full grid grid-cols-subgrid items-center" data-phase={props.lane.phase}>
        <div class="flex min-w-0 items-center gap-2">
          <span aria-hidden="true" class="grid size-mark flex-none place-items-center *:size-full" innerHTML={termMark(props.segment.term)} />
          <span class="min-w-0 text-small leading-snug font-medium text-ink @max-sm:hidden">{props.segment.tag}</span>
        </div>
        <div class="relative grid items-center" ref={track}>
          <span aria-hidden="true" class="absolute inset-x-0 top-1/2 h-1 -translate-y-1/2">
            <span class="absolute inset-x-0 top-1/2 -translate-y-1/2 border-t-ring border-rule" />
            <span class="curriculum-glide absolute top-0 left-0 h-full bg-quiet" ref={before} />
            <span class="curriculum-glide absolute top-0 left-0 h-full bg-denim-mark" ref={after} />
          </span>
          <span
            aria-hidden="true"
            class="absolute top-1/2 grid size-key-mark -translate-1/2 place-items-center *:size-full"
            innerHTML={termMark(props.segment.term)}
            style={{ left: `${100 * along(props.segment.end + 1)}%` }}
          />
          <div class="curriculum-glide relative w-curriculum-screen justify-self-start @max-sm:w-curriculum-screen-narrow" ref={screen}>
            <div class="curriculum-glass relative isolate rounded-1 bg-quiet p-1">
              <div class="relative overflow-hidden rounded-swatch">
                <canvas
                  aria-label={`${props.segment.tag}, an episode of the batch standing at its start on the way`}
                  class="pixelated block h-auto w-full"
                  height={LENS.height}
                  ref={canvas}
                  role="img"
                  width={LENS.width}
                />
                <span aria-hidden="true" class="curriculum-gray pointer-events-none absolute inset-0 backdrop-grayscale backdrop-brightness-112 backdrop-contrast-72" />
              </div>
            </div>
          </div>
          <span class={[LABEL, 'curriculum-glide absolute bottom-0 left-0 font-semibold whitespace-nowrap text-denim-text tabular-nums @max-sm:hidden']} ref={far}>
            {props.far}
          </span>
        </div>
      </li>
    )
  }
})
