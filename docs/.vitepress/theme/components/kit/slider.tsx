import { clamp }                                               from '@vueuse/core'
import { type HTMLAttributes, type PropType, defineComponent } from 'vue'

import type { Band }  from '../../../lib/widgets/band.ts'
import type { Scrub } from '../../../lib/widgets/scrub.ts'

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
 * The classes of a slider laid over the whole of the drawing beside it, the
 * control taking no text selection as a pointer drags across it.
 */
export const OVER: Parts = {
  control : 'absolute inset-0 select-none',
  root    : 'absolute inset-0',
  thumb   : 'absolute inset-0'
}

/**
 * The classes of a slider wrapped around the drawing its control holds, the
 * thumb laid over the drawing and its ring following the drawing's corners.
 */
export const AROUND: Parts = {
  control : 'select-none',
  root    : 'relative',
  thumb   : 'absolute inset-0 rounded-1'
}

/**
 * The classes of the parts of a drawing that serves as its own slider, its
 * control showing the cursor that drags it while a touch still scrolls the
 * page, and its thumb ringed while it has focus and passing a pointer's press
 * through to the drawing.
 */
export const SCRUB_PARTS = {
  control : 'cursor-ew-resize touch-pan-y',
  thumb   : 'focus-ring pointer-events-none'
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
 * alone, it lays its control and its thumb as those classes place them, over
 * the drawing beside it or around the drawing its control holds. Given a
 * `band`, its control takes the band's press in place of the slider's own.
 */
export const Slider = defineComponent({
  name: 'Slider',

  props: {
    at    : { default: null, type: Number as PropType<number | null> },
    band  : { default: null, type: Object as PropType<Band | null> },
    parts : { default: () => BAR, type: Object as PropType<Parts> },
    scrub : { required: true, type: Object as PropType<Scrub> }
  },

  setup: (props, { slots }) => () => {
    const { at, band, parts, scrub } = props
    const along                      = at === null ? null : `${100 * clamp(scrub.shareOf(at), 0, 1)}%`

    return (
      <div {...scrub.root.value} class={parts.root}>
        <div {...(band ?? scrub).control.value} class={[SCRUB_PARTS.control, parts.control]}>
          {along === null ? slots.default?.() : [
            <span class={BAR.track} />,
            <span class={BAR.fill} style={{ width: along }} />
          ]}
        </div>
        <div
          {...scrub.thumb.value}
          class={[SCRUB_PARTS.thumb, parts.thumb]}
          ref={band?.thumb}
          style={along === null ? undefined : { left: along }}
        />
      </div>
    )
  }
})
