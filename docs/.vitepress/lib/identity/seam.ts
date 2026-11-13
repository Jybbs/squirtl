import { type Ref, computed, ref } from 'vue'

import * as logo                from '../marks/logo.ts'
import { useScrub }             from '../widgets/scrub.ts'
import { IDENTITY, type Scheme } from './identity.ts'
import { SCHEMES, namedOf }     from './palette.ts'

/**
 * One entry of a ground's key to the trail, what the color marks, its hex, and
 * its name.
 */
export interface Entry {
  hex  : string
  name : string
  what : string
}

/**
 * The logo the widget fills, the whole name laid out as the mark.
 */
export const MARK = logo.markOf(IDENTITY.name)

/**
 * The dots of the mark the fill steps through, the trail's in the order Blue
 * walks them and then the dots still ahead of him, every dot in ink left out
 * since it stands lit whatever the fill.
 */
export const FILLED: readonly logo.Dot[] = [
  ...MARK.dots.filter((dot): dot is Extract<logo.Dot, { kind: 'trail' }> => dot.kind === 'trail').toSorted((a, b) => a.step - b.step),
  ...MARK.dots.filter(dot => dot.kind === 'ahead')
]

/**
 * The positions the seam between the grounds stands at, from 0, every part of
 * the logo on the dark ground, to 100, every part on the light.
 */
export const SEAM = 101

/**
 * The seam's positions on its nudge the first time the widget shows, standing
 * a longer beat where it begins, then a step toward the dark ground and back
 * past the middle toward the light before it settles where it began.
 */
export const NUDGE = [50, 50, 44, 38, 44, 50, 56, 62, 56, 50] as const

/**
 * The beat the fill lights a dot at and the one the seam's nudge moves at, in
 * milliseconds, the nudge waiting a longer beat before it starts.
 */
export const TEMPO = { fill: 160, nudge: 60, wait: 400 }

/**
 * What each third of the trail marks, from the oldest.
 */
const THIRDS = ['The first third, oldest', 'The middle third', 'The last third, newest']

/**
 * Makes the entry of a key to the trail marking `what` in the color `token`
 * names.
 */
function entryOf(token: string, what: string): Entry {
  const { hex, name } = namedOf(token)
  return { hex, name, what }
}

/**
 * Lists the key to the trail on `scheme`'s ground, the trail's thirds from the
 * oldest and then the dot still ahead, each beside its color.
 */
export function keyOf(scheme: Scheme): Entry[] {
  const { ahead, thirds } = IDENTITY.logo[scheme]

  return [...thirds.map((token, n) => entryOf(token, THIRDS[n]!)), entryOf(ahead, 'The dot still ahead')]
}

/**
 * Describes the seam at `at` as a screen reader reads it.
 */
export function seamWords(at: number): string {
  if (at >= SEAM - 1) return 'The light ground alone'
  if (at <= 0) return 'The dark ground alone'
  return `${at}% on the light ground, ${SEAM - 1 - at}% on the dark`
}

/**
 * Holds the seam between the grounds and the fill along the trail while the
 * widget at `box` shows, the seam nudging once toward each ground and back
 * the first time it shows and the fill lighting a dot a beat and starting
 * over, a reader's drag on the strip or the range holding either where it
 * lands.
 *
 * Returns:
 *   The seam's position, the fill's, the last position the fill reaches, the
 *   hex the dot the fill stands on takes on each ground, and the slider over
 *   each.
 */
export function useSeam(box: Ref<HTMLElement | undefined>) {
  const at     = ref<number>(NUDGE[0])
  const nudged = ref(0)
  const fill   = ref(0)
  const last   = FILLED.length - 1
  const strip  = useScrub(box, {
    beat   : () => nudged.value === 1 ? TEMPO.wait : TEMPO.nudge,
    done   : () => nudged.value >= NUDGE.length - 1,
    finish : () => { nudged.value = NUDGE.length - 1 },
    tick   : () => { at.value = NUDGE[++nudged.value]! }
  }, {
    at,
    count    : SEAM,
    describe : seamWords,
    label    : 'Move the seam between the light and the dark ground',
    seek     : n => {
      nudged.value = NUDGE.length - 1
      at.value     = n
    }
  })
  const trail  = useScrub(box, {
    beat    : TEMPO.fill,
    done    : () => fill.value >= last,
    finish  : () => { fill.value = last },
    restart : () => { fill.value = 0 },
    tick    : () => { fill.value++ }
  }, { at: fill, count: last + 1, describe: n => `Dot ${n + 1} of ${last + 1}`, label: 'The trail', seek: n => { fill.value = n } })

  return {
    at    : at,
    fill  : fill,
    last  : last,
    lit   : computed(() => Object.fromEntries(SCHEMES.map(scheme => [scheme, logo.paintOf(FILLED[fill.value]!, scheme)])) as Record<Scheme, string>),
    strip : strip,
    trail : trail
  }
}
