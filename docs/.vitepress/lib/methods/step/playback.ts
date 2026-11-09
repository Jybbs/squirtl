import { type ComputedRef, type Ref, computed, ref } from 'vue'

import { type Band, cellAt, useBand } from '../../widgets/band.ts'
import { type Scrub, useScrub }       from '../../widgets/scrub.ts'
import * as step                      from '../step.ts'

/**
 * The positions the sheet stands at, one to each frame of each step.
 */
const CELLS = step.STEPS.length * step.FRAMES

/**
 * The sheet as the widget plays it: the cell it stands on, the step and frame
 * that cell names, the slider over the cells, and the band a pointer picks a
 * cell on.
 */
export interface StepPlayback {
  at    : Ref<number>
  band  : Band
  scrub : Scrub
  where : ComputedRef<ReturnType<typeof step.cellOf>>
}

/**
 * Plays the sheet a frame a beat while the widget at `box` shows, resting on
 * the frame PyBoy draws, and holds it on the cell the slider names or a pointer
 * picks, a press moving focus to the slider's `thumb`.
 */
export function useStepPlayback(box: Ref<HTMLElement | undefined>, thumb: Ref<HTMLElement | undefined>, label: string): StepPlayback {
  const at    = ref(CELLS - 1)
  const where = computed(() => step.cellOf(at.value))
  const scrub = useScrub(box, {
    beat   : () => where.value.f === step.FRAMES ? step.TEMPO.rest : step.TEMPO.tick,
    done   : () => false,
    finish : () => { at.value = CELLS - 1 },
    tick   : () => { at.value = (at.value + 1) % CELLS }
  }, {
    at,
    count    : CELLS,
    describe : position => step.describe(position),
    label,
    page     : step.FRAMES,
    seek     : position => { at.value = position }
  })

  const band = useBand(scrub, thumb, event => {
    const [f, s] = cellAt(event, step.FRAMES, step.STEPS.length)
    at.value     = s * step.FRAMES + f
  })

  return { at, band, scrub, where }
}
