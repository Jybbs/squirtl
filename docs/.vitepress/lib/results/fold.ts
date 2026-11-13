import { useElementVisibility, useTransition }       from '@vueuse/core'
import { type ComputedRef, type Ref, computed, ref } from 'vue'

import { BEAT, TRAVEL, useMotion }               from '../widgets/motion.ts'
import { fromMouse }                             from '../widgets/scrub.ts'
import { useDrawnWidth }                         from '../widgets/width.ts'
import { type Side, finalsWidth }                from './lanes.ts'
import { lanesOf }                               from './layout.ts'
import { legendOf }                              from './legend.ts'
import { COMMITTED, type Results, groupsOf }     from './results.ts'

/**
 * The listeners a side of the figure takes, widening it while a mouse rests on
 * it or it holds focus, and focusing it on a touch.
 */
export interface SideListeners {
  onBlur         : () => void
  onFocus        : () => void
  onPointerdown  : (event: PointerEvent) => void
  onPointerenter : (event: PointerEvent) => void
  onPointerleave : (event: PointerEvent) => void
}

/**
 * Widens the side of a figure `width` wide that a mouse rests on, or else the
 * side holding focus, folding the other, and eases the last evaluation's width
 * there over one glide, landing at once under reduced motion.
 *
 * Returns:
 *   The width the last evaluation takes, the side widened, and the listeners
 *   each side takes.
 */
function useFold(width: Ref<number>): {
  finals    : ComputedRef<number>
  listeners : (side: Side) => SideListeners
  side      : ComputedRef<Side | null>
} {
  const motion  = useMotion()
  const hovered = ref<Side | null>(null)
  const focused = ref<Side | null>(null)
  const side    = computed(() => hovered.value ?? focused.value)
  const finals  = useTransition(() => finalsWidth(width.value, side.value), {
    disabled : computed(() => !motion.value),
    duration : 2 * BEAT,
    easing   : TRAVEL
  })

  return {
    finals    : finals,
    listeners : each => ({
      onBlur         : () => { focused.value = null },
      onFocus        : () => { focused.value = each },
      onPointerdown  : event => { if (event.pointerType === 'touch') (event.currentTarget as HTMLElement).focus() },
      onPointerenter : event => { if (fromMouse(event)) hovered.value = each },
      onPointerleave : event => { if (fromMouse(event)) hovered.value = null }
    }),
    side : side
  }
}

/**
 * Plays the figure in once `seen` holds: each seed's row traces out along the
 * steps over two glides, the rows a beat apart down each lane, and each seed's
 * last evaluation rises from its random share over one glide, the lanes a beat
 * apart, every part standing whole at once under reduced motion.
 *
 * Returns:
 *   How far each seed's row has traced out and each lane's seeds have risen,
 *   from 0 to 1.
 */
function useEntrance(seen: Ref<boolean>, seeds: number, lanes: number): {
  bells : ComputedRef<number>[]
  rows  : ComputedRef<number>[]
} {
  const motion   = useMotion()
  const disabled = computed(() => !motion.value)
  const shown    = () => seen.value || disabled.value ? 1 : 0
  const played   = (count: number, glides: number) => Array.from({ length: count }, (_, n) =>
    useTransition(shown, { delay: n * BEAT, disabled, duration: 2 * glides * BEAT, easing: TRAVEL }))

  return { bells: played(lanes, 1), rows: played(seeds, 2) }
}

/**
 * Draws the comparison of the runs `results` holds, the committed runs unless
 * given others, in `box`, measuring the width it takes there, playing it in
 * once `box` first comes into view, and widening the side a reader points at
 * or focuses, its legend's hatching drawn through the pattern `hatch`.
 *
 * Returns:
 *   The figure laid out, how far it has played in, the groups, the legend,
 *   the listeners each side takes, and the width drawn at.
 */
export function useComparison(box: Ref<HTMLElement | undefined>, hatch: string, results: Results = COMMITTED) {
  const groups   = groupsOf(results)
  const width    = useDrawnWidth(box, 240)
  const seen     = useElementVisibility(box, { once: true })
  const fold     = useFold(width)
  const entrance = useEntrance(seen, Math.max(0, ...groups.map(group => group.runs.length)), groups.length)

  return {
    drawn     : computed(() => lanesOf(groups, width.value, fold.finals.value)),
    entrance  : entrance,
    groups    : groups,
    legend    : results.random === null ? [] : legendOf(groups, results.random, hatch),
    listeners : fold.listeners,
    width     : width
  }
}
