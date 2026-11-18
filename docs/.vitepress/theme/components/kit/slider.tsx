import { clamp }                                              from '@vueuse/core'
import { type HTMLAttributes, type PropType, defineComponent } from 'vue'

import type { Scrub }  from '../../../lib/widgets/scrub.ts'
import { SCRUB_PARTS } from './widget.ts'

/**
 * The classes laying out a slider's root, its control, and its thumb, beside
 * the ones every slider's control and thumb take.
 */
export interface Parts {
  control : HTMLAttributes['class']
  root    : HTMLAttributes['class']
  thumb   : HTMLAttributes['class']
}

/**
 * The classes of a bar: its track and its fill across the middle of the
 * control, and a ringed thumb centered on the end of the fill.
 */
const BAR = {
  control : 'relative h-6 select-none',
  fill    : 'absolute top-1/2 left-0 h-1 -translate-y-1/2 rounded-full bg-denim-mark',
  root    : 'relative',
  thumb   : 'absolute top-1/2 size-4 -translate-1/2 rounded-full border-ring border-lift bg-denim-mark',
  track   : 'absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-rule'
}

/**
 * A widget's slider on `scrub`. Given the position `at`, it draws a bar whose
 * fill and thumb stand at the share of its length `at` takes. Given `parts`
 * alone, it lays its control and its thumb over the drawing beside it, as
 * those classes place them.
 */
export const Slider = defineComponent({
  name: 'Slider',

  props: {
    at    : { default: null, type: Number as PropType<number | null> },
    parts : { default: () => BAR, type: Object as PropType<Parts> },
    scrub : { required: true, type: Object as PropType<Scrub> }
  },

  setup: props => () => {
    const { at, parts, scrub } = props
    const along                = at === null ? null : `${100 * clamp(scrub.shareOf(at), 0, 1)}%`

    return (
      <div {...scrub.root.value} class={parts.root}>
        <div {...scrub.control.value} class={[SCRUB_PARTS.control, parts.control]}>
          {along === null ? null : [
            <span class={BAR.track} />,
            <span class={BAR.fill} style={{ width: along }} />
          ]}
        </div>
        <div
          {...scrub.thumb.value}
          class={[SCRUB_PARTS.thumb, parts.thumb]}
          style={along === null ? undefined : { left: along }}
        />
      </div>
    )
  }
})
