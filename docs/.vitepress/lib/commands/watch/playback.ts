import { type ComputedRef, type Ref, computed, ref } from 'vue'

import { type Band, cellAt, useBand } from '../../widgets/band.ts'
import { type Scrub, useScrub }       from '../../widgets/scrub.ts'
import * as watching                  from '../watch.ts'

/**
 * The playback as the widget runs it: the milliseconds it stands at, the step
 * that time reaches, the slider over the recording's presses with its control
 * taking a press of its own, and the handlers holding the playback on the byte
 * a pointer presses or drags across.
 */
export interface WatchPlayback extends Band {
  scrub : Scrub
  step  : ComputedRef<number>
  t     : Ref<number>
}

/**
 * Reads the byte of the band a pointer `event` rests on, the
 * band laid out in as many columns as its grid template names.
 */
function byteAt(event: PointerEvent): number {
  const columns       = getComputedStyle(event.currentTarget as HTMLElement).gridTemplateColumns.split(' ').length
  const [column, row] = cellAt(event, columns, Math.ceil(watching.LAST / columns))
  return Math.min(row * columns + column + 1, watching.LAST)
}

/**
 * Plays the recording at sixty steps a second while the widget at `box`
 * shows, holding it at the byte the slider names, a press on the band moving
 * focus to the slider's `thumb`.
 */
export function useWatchPlayback(box: Ref<HTMLElement | undefined>, thumb: Ref<HTMLElement | undefined>, label: string): WatchPlayback {
  const t    = ref(0)
  const step = computed(() => watching.stepAt(t.value))
  const at   = computed({
    get : () => Math.max(1, step.value),
    set : value => { t.value = watching.timeOf(value) }
  })

  const scrub = useScrub(box, {
    beat    : 1000 / watching.RATE,
    done    : () => t.value >= watching.PHASES.close,
    finish  : () => { t.value = watching.PHASES.hold },
    rest    : 0,
    restart : () => { t.value = 0 },
    tick    : () => { t.value = Math.min(watching.PHASES.close, t.value + 1000 / watching.RATE) }
  }, {
    at,
    count    : watching.LAST + 1,
    describe : n => watching.describe(Math.max(1, n)),
    label,
    seek     : value => { at.value = Math.max(1, value) }
  })

  const band = useBand(scrub, thumb, event => { at.value = byteAt(event) })

  return { ...band, scrub, step, t }
}
