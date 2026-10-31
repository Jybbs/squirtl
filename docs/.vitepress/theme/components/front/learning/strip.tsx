import { type PropType, type VNode, defineComponent, ref } from 'vue'

import type { Moment }   from '../../../../lib/front/learning.ts'
import * as strip        from '../../../../lib/front/learning/strip.ts'
import type { Hue }      from '../../../../lib/identity/identity.ts'
import { counted }       from '../../../../lib/widgets/numbers.ts'
import type { Scrub }    from '../../../../lib/widgets/scrub.ts'
import { useDrawnWidth } from '../../../../lib/widgets/width.ts'
import * as clock        from '../../kit/clock.tsx'
import { SCRUB_PARTS }   from '../../kit/widget.ts'
import { WalkBands }     from './bands.tsx'

/**
 * The classes laying out the strip as the slider's control beside the ones
 * every slider's control takes, a press or a drag along it moving the clock.
 */
const CONTROL = 'focus-ring-within grid rounded-1 select-none'

/**
 * The strip's geometry.
 */
const STRIP = strip.STRIP

/**
 * The classes stacking the slider's thumb over the strip's left edge, taking no
 * width so a pointer's press lands on the drawing.
 */
const THUMB = 'col-start-1 row-start-1 justify-self-start outline-none'

/**
 * The name a screen reader reads for the strip's drawing.
 */
const WORDS = 'Each walk’s presses on one clock, a band to a walk in its hue, the coin’s presses hatched and '
            + 'the table’s solid, with a pin of each walk’s Blue where it reaches the north edge'

/**
 * Draws the clock's line at `now` and its chip at `left`, naming the presses
 * `at` the clock stands at.
 */
function drawStripClock(at: number, left: number, now: number, rows: strip.Rows): VNode {
  return (
    <g>
      {clock.drawClockLine(rows.pins, STRIP.top - STRIP.overhang, now)}
      {clock.drawClockChip(left, counted(at, 'press', 'presses'), STRIP.chip)}
    </g>
  )
}

/**
 * The strip of every walk's presses on the clock they share, a band to a walk
 * in its hue under the clock's line and its chip, which serves as the slider
 * `scrub` makes of the clock and reports the walk a mouse points at through
 * `point`.
 */
export const WalkStrip = defineComponent({
  emits : ['point'],
  name  : 'WalkStrip',

  props: {
    at      : { required: true, type: Number },
    hues    : { required: true, type: Array as PropType<readonly Hue[]> },
    id      : { required: true, type: String },
    moments : { required: true, type: Array as PropType<readonly Moment[]> },
    picked  : { default: null, type: Number as PropType<number | null> },
    scrub   : { required: true, type: Object as PropType<Scrub> }
  },

  setup: (props, { emit }) => {
    const drawing = ref<SVGSVGElement>()
    const width   = useDrawnWidth(drawing, STRIP.least)
    const rows    = strip.stripRows(props.moments.length)

    return () => {
      const wide                 = width.value
      const { ended, left, now } = strip.stripClockAt(props.at, props.moments, wide)
      return (
        <div
          {...props.scrub.root.value}
          class="px-3"
          onPointerleave={() => emit('point', null)}
          onPointermove={(event: PointerEvent) => emit('point', strip.walkUnder(event, props.moments.length))}
        >
          <div {...props.scrub.control.value} class={[SCRUB_PARTS.control, CONTROL]}>
            <svg
              aria-label={WORDS}
              class="col-start-1 row-start-1 block h-auto w-full overflow-visible"
              ref={drawing}
              role="img"
              viewBox={`0 0 ${wide} ${rows.height}`}
            >
              {clock.drawReveal(rows.height, `${props.id}-reveal`, now + 1)}
              <WalkBands
                ended={ended}
                hues={props.hues}
                id={props.id}
                moments={props.moments}
                picked={props.picked}
                width={wide}
              />
              {drawStripClock(props.at, left, now, rows)}
            </svg>
            <span {...props.scrub.thumb.value} class={THUMB} />
          </div>
        </div>
      )
    }
  }
})
