import type * as toggleGroup                     from '@zag-js/toggle-group'
import { type ComputedRef, computed, ref, watch } from 'vue'

import { type Options, useSwitches } from '../widgets/choice.ts'
import { BEAT, useMotion }           from '../widgets/motion.ts'
import { COMMITTED }                 from './results.ts'

/**
 * The listeners a seed's switch takes, by the event each one hears.
 */
type Listeners = Record<`on${string}`, (event: Event) => void>

/**
 * The seeds kept and their switches: the list each switch is set in, the
 * listeners each switch takes, the seeds kept as numbers, the switches'
 * props, and the call switching one seed.
 */
export interface Seeds {
  flipped  : (Element | null)[]
  press    : Listeners
  seeds    : ComputedRef<number[]>
  switches : Options<string>
  toggle   : (seed: number) => void
}

/**
 * The hop a seed's switch gives as its seed is kept, leaping up and rocking
 * to one side and back as its run's Poké Ball fills.
 */
const KEEP: Keyframe[] = [
  { transform: 'translateY(0px) rotate(0deg)' },
  { transform: 'translateY(-4px) rotate(-3deg)' },
  { transform: 'translateY(1px) rotate(2deg)' },
  { transform: 'translateY(0px) rotate(0deg)' }
]
/**
 * The shake a seed's switch gives as its seed is left out, slipping side to
 * side a pixel low as its run's Poké Ball empties, as a ball shakes when the
 * Pokémon inside breaks free.
 */
const LEAVE: Keyframe[] = [
  { transform: 'translate(0px, 0px) rotate(0deg)' },
  { transform: 'translate(-3px, 1px) rotate(-2deg)' },
  { transform: 'translate(3px, 1px) rotate(2deg)' },
  { transform: 'translate(-1px, 1px) rotate(0deg)' },
  { transform: 'translate(0px, 0px) rotate(0deg)' }
]
/**
 * The press a seed's switch gives while it is held down, shrinking and
 * sinking a pixel over half a beat and holding there.
 */
const PRESS = {
  keyframes : [{ scale: '1', translate: '0px 0px' }, { scale: '0.9', translate: '0px 1px' }],
  timing    : { duration: BEAT / 2, easing: 'ease-out', fill: 'forwards' }
} as const satisfies { keyframes: Keyframe[], timing: KeyframeAnimationOptions }
/**
 * The spring a seed's switch gives as it is let go, swelling past its size
 * and settling back, after the place it is let go from.
 */
const SPRING: Keyframe[] = [
  { scale: '1.08', translate: '0px -1px' },
  { scale: '0.98', translate: '0px 0px' },
  { scale: '1', translate: '0px 0px' }
]
/**
 * The seeds every group's runs and random presses trained and played under,
 * read from the runs the repository commits, from the lowest.
 */
export const committedSeeds: readonly number[] = [...new Set(COMMITTED.runs.map(run => run.seed))]
  .toSorted((a, b) => a - b)

/**
 * Calls `act` with a key event only where Space or Enter, the keys pressing a
 * button, went down or up, leaving a key held down to repeat.
 */
const keyed = (act: (event: Event) => void) => (event: Event) => {
  const { key, repeat } = event as KeyboardEvent
  if ((key === ' ' || key === 'Enter') && !repeat) act(event)
}

/**
 * Hops each seed's switch over `duration` milliseconds as `seeds` keeps its
 * seed and shakes it as `seeds` leaves its seed out, none under reduced
 * motion.
 *
 * Returns:
 *   The list each seed's switch is set in, the lowest seed first.
 */
function useFlipped(duration: number, seeds: () => readonly number[]): (Element | null)[] {
  const switches: (Element | null)[] = []
  const timing                       = { duration, easing: 'ease-out' }
  watchSwitched(seeds, (k, kept) => switches[k]?.animate(kept ? KEEP : LEAVE, timing))
  return switches
}

/**
 * Sinks a seed's switch while a pointer, Space, or Enter holds it down and
 * springs it back over `spring` milliseconds once it is let go, none under
 * reduced motion.
 *
 * Returns:
 *   The listeners each switch takes.
 */
function usePress(spring: number): Listeners {
  const motion = useMotion()
  const held   = new Map<HTMLElement, Animation>()

  const down = (event: Event) => {
    const part = event.currentTarget as HTMLElement
    if (motion.value && !held.has(part)) held.set(part, part.animate(PRESS.keyframes, PRESS.timing))
  }
  const up = (event: Event) => {
    const part  = event.currentTarget as HTMLElement
    const press = held.get(part)
    if (!press) return
    held.delete(part)
    const { scale, translate } = getComputedStyle(part)
    press.cancel()
    part.animate([{ scale, translate }, ...SPRING], { duration: spring, easing: 'ease-out' })
  }

  return {
    onBlur          : up,
    onKeydown       : keyed(down),
    onKeyup         : keyed(up),
    onPointercancel : up,
    onPointerdown   : event => { if ((event as PointerEvent).button === 0) down(event) },
    onPointerleave  : up,
    onPointerup     : up
  }
}

/**
 * Holds the seeds kept as a group of switches laid along the orientation
 * `orientation` reads, never letting the last one go, and switches one seed
 * from anywhere else a reader presses it, each switch sinking as it is
 * pressed and hopping or shaking over `duration` milliseconds as its seed is
 * kept or left out.
 */
export function useSeeds(duration: number, orientation?: () => toggleGroup.Props['orientation']): Seeds {
  const names    = committedSeeds.map(String)
  const kept     = ref<ReadonlySet<string>>(new Set(names))
  const switches = useSwitches(names, kept, orientation)
  const seeds    = computed(() => committedSeeds.filter(seed => kept.value.has(`${seed}`)))
  let last       = kept.value

  watch(kept, now => {
    if (now.size === 0) kept.value = last
    else last = now
  })

  return {
    flipped  : useFlipped(duration, () => seeds.value),
    press    : usePress(duration),
    seeds    : seeds,
    switches : switches,
    toggle   : seed => {
      const now  = new Set(kept.value)
      const each = `${seed}`
      if (!now.delete(each)) now.add(each)
      kept.value = now
    }
  }
}

/**
 * Calls `play` with the place and the new value of each of `values` that
 * changed, none under reduced motion.
 */
export function watchChanged<Value>(
  values : () => readonly Value[],
  play   : (n: number, now: Value) => void
): void {
  const motion = useMotion()
  watch(values, (now, before) => {
    if (!motion.value) return
    now.forEach((value, n) => {
      if (value !== before[n]) play(n, value)
    })
  })
}

/**
 * Calls `play` with the place of each seed `seeds` switches and whether it is
 * now kept, none under reduced motion.
 */
export const watchSwitched = (seeds: () => readonly number[], play: (k: number, kept: boolean) => void) =>
  watchChanged(() => committedSeeds.map(seed => seeds().includes(seed)), play)
