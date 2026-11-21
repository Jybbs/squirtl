import { type ComputedRef, type Ref, computed, ref } from 'vue'

import { IDLE }                 from '../../widgets/autoplay.ts'
import { count }                from '../../widgets/numbers.ts'
import { type Scrub, useScrub } from '../../widgets/scrub.ts'
import { useDrawnWidth }        from '../../widgets/width.ts'
import * as discount            from '../discount.ts'

/**
 * The discount as the widget sets it: the discount its handle stands at, the
 * width the chart draws at, the plot of the weights under that discount at
 * that width, and the slider over the handle's stops.
 */
export interface DiscountPlayback {
  plot  : ComputedRef<discount.WeightPlot>
  scrub : Scrub
  set   : ComputedRef<number>
  width : ComputedRef<number>
}

/**
 * Describes the half point at `stop` for a screen reader.
 */
function describe(stop: number): string {
  const at = discount.discountAt(stop)
  return `Discount ${discount.spelled(at)}, `
       + `half its weight at ${count(Math.round(discount.halfLife(at)))} steps`
}

/**
 * Opens the discount on the one the settings declare and holds it at the stop
 * the slider names, drawing the chart at the width of the widget at `box`,
 * which never plays on its own.
 */
export function useDiscountPlayback(box: Ref<HTMLElement | undefined>, label: string): DiscountPlayback {
  const at    = ref(discount.stopOf(discount.DISCOUNT))
  const width = useDrawnWidth(box, discount.LEAST)
  const set   = computed(() => discount.discountAt(at.value))
  const plot  = computed(() => discount.plotOf(set.value, width.value))
  const scrub = useScrub(box, IDLE, {
    at,
    count : discount.WEIGHING.stops + 1,
    describe,
    label,
    seek  : stop => { at.value = stop }
  })

  return { plot, scrub, set, width }
}
