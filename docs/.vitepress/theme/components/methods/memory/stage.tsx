import { type PropType, computed, defineComponent, ref, watch } from 'vue'

import { useRoomFades }     from '../../../../lib/game/fades.ts'
import type * as rooms      from '../../../../lib/game/rooms.ts'
import { SQUARE }           from '../../../../lib/game/screen.ts'
import * as marks           from '../../../../lib/methods/memory/marks.ts'
import { paintMap }         from '../../../../lib/methods/memory/paint.ts'
import { FADE, type Frame } from '../../../../lib/methods/memory/play.ts'
import { MemoryOverlay }    from './overlay.tsx'

/**
 * Reads the square of the map fitted at `fit` under a pointer at `x` and `y`
 * on a plate drawn at `box`, or none where the pointer rests off the map.
 */
function squareAt(box: DOMRect, fit: marks.Fit, x: number, y: number): rooms.Square | null {
  const scale = marks.PLATE.width / box.width
  const c     = Math.floor(((x - box.left) * scale - fit.left) / fit.cell)
  const r     = Math.floor(((y - box.top) * scale - fit.top) / fit.cell)
  return c >= 0 && r >= 0 && c < fit.cols && r < fit.rows ? [c, r] : null
}

/**
 * The map Blue stands on drawn whole on its plate, the squares reached and the
 * people over it, beneath the overlay holding the flags' sites, the column and
 * row ticks, and the bytes' square. A pointer resting on a square names it to
 * the widget.
 */
export const MemoryStage = defineComponent({
  emits : ['point'],
  name  : 'MemoryStage',

  props: {
    frame   : { required: true, type: Object as PropType<Frame> },
    lit     : { default: null, type: Number as PropType<number | null> },
    pointed : { default: null, type: Array as unknown as PropType<rooms.Square | null> }
  },

  setup: (props, { emit }) => {
    const canvas = ref<HTMLCanvasElement>()
    const stage  = ref<HTMLElement>()
    const faded  = useRoomFades(FADE)
    const fit    = computed(() => marks.fitOf(props.frame.place))

    const paint = () => {
      const context = canvas.value?.getContext('2d')
      if (context) paintMap(context, faded.value.get(props.frame.place)?.map, props.frame, props.lit)
    }

    const point = (event: PointerEvent) => {
      const next = squareAt(stage.value!.getBoundingClientRect(), fit.value, event.clientX, event.clientY)
      if (String(next) !== String(props.pointed)) emit('point', next)
    }

    watch([() => props.frame, () => props.lit, faded], paint, { flush: 'post' })

    return () => {
      const { cols, height, left, rows, top, width } = fit.value
      const { PLATE }                                = marks
      return (
        <div class="memory-stage relative w-full cursor-crosshair touch-pan-y" onPointerleave={() => emit('point', null)} onPointermove={point} ref={stage}>
          <canvas
            aria-hidden="true"
            class="pixelated absolute"
            height={rows * SQUARE}
            ref={canvas}
            style={{ height: `${100 * height / PLATE.height}%`, left: `${100 * left / PLATE.width}%`, top: `${100 * top / PLATE.height}%`, width: `${100 * width / PLATE.width}%` }}
            width={cols * SQUARE}
          />
          <MemoryOverlay fit={fit.value} frame={props.frame} lit={props.lit} target={props.pointed ?? props.frame.square} />
        </div>
      )
    }
  }
})
