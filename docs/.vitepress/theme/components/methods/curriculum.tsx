import { defineComponent, ref } from 'vue'

import { RoomImages }                 from '../../../lib/game/images.ts'
import * as curriculum                from '../../../lib/methods/curriculum.ts'
import { useCurriculumPlayback }      from '../../../lib/methods/curriculum/playback.ts'
import { DETAIL, LABEL, SCRUB_PARTS } from '../kit/widget.ts'
import { CurriculumLane }             from './curriculum/lane.tsx'

/**
 * The words the widget sets.
 */
const WORDS = {
  lanes  : 'A lane for each segment, its episode’s screen standing at its start on the way from the bedroom',
  slider : 'The batches of the run, each segment’s screen standing at its start in its lane, held at the batch it names'
}

/**
 * The window moving back along the recording: a lane for each segment over
 * the places from the bedroom to Oak’s lab, its screen standing at the start
 * of one episode of the batch with gray behind it as far as the recording
 * carries Blue, Denim ahead of it to the goal, and beside it how far before the
 * goal the episode starts. Each batch replays the recording up to every start in gray, the
 * gray wiping off toward the bedroom as the agent takes over, and batch by
 * batch the screens glide left toward the bedroom. The slider beneath holds the
 * run at a batch.
 */
export const MethodsCurriculum = defineComponent({
  name  : 'MethodsCurriculum',
  setup : () => {
    const box                 = ref<HTMLElement>()
    const images              = new RoomImages()
    const { at, lanes, scrub } = useCurriculumPlayback(box, WORDS.slider)

    return () => (
      <div class="@container grid gap-2" ref={box}>
        <div class="curriculum-drawing grid gap-y-1">
          <ol aria-label={WORDS.lanes} class="curriculum-lanes col-span-full grid grid-cols-subgrid gap-y-1">
            {curriculum.SEGMENTS.map((segment, k) => (
              <CurriculumLane
                far={curriculum.farOf(at.value, k)}
                images={images}
                lane={lanes.value[k]!}
                segment={segment}
                start={curriculum.RUN[at.value]![k]!.start}
              />
            ))}
          </ol>
          <div aria-hidden="true" class="col-start-2 flex h-7 border-t-hairline border-quiet @max-sm:h-curriculum-places">
            {curriculum.STRETCHES.map(stretch => (
              <span class="curriculum-band relative min-w-0 flex-none" style={{ flexBasis: `${100 * (stretch.last - stretch.first + 1) / (curriculum.LAST + 1)}%` }}>
                <span class={[LABEL, 'curriculum-place absolute font-semibold whitespace-nowrap text-ink']}>{stretch.name}</span>
              </span>
            ))}
          </div>
        </div>
        <div class="flex items-center gap-3">
          <span aria-hidden="true" class={[DETAIL, 'w-curriculum-head flex-none whitespace-nowrap text-ink tabular-nums']}>{curriculum.batchName(at.value)}</span>
          <div {...scrub.root.value} class="relative min-w-0 flex-auto">
            <div {...scrub.control.value} class={[SCRUB_PARTS.control, 'relative h-6 select-none']}>
              <span class="absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-rule" />
              <span class="absolute top-1/2 left-0 h-1 -translate-y-1/2 rounded-full bg-denim-mark" style={{ width: `${100 * at.value / (curriculum.BATCHES - 1)}%` }} />
            </div>
            <div {...scrub.thumb.value} class={[SCRUB_PARTS.thumb, 'absolute top-1/2 size-4 -translate-1/2 rounded-full border-ring border-lift bg-denim-mark']} style={{ left: `${100 * at.value / (curriculum.BATCHES - 1)}%` }} />
          </div>
        </div>
      </div>
    )
  }
})
