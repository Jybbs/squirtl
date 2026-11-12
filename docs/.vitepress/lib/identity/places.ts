import { type Ref, ref } from 'vue'

import type { Project } from '../config/navigation.ts'
import { useAutoplay }  from '../widgets/autoplay.ts'
import { useChoice }    from '../widgets/choice.ts'
import { fromMouse }    from '../widgets/scrub.ts'

/**
 * A place the tagline or the byline is read in, the name its tab reads.
 */
export type Place = 'card' | 'github' | 'readme'

/**
 * One badge the README opens on, the name its icon stands for and the value
 * beside it.
 */
export interface Badge {
  name  : string
  value : string
}

/**
 * The places the widget folds between, in the order their tabs stand, each
 * beside the name its tab reads.
 */
export const PLACES: readonly { name: string, place: Place }[] = [
  { name: 'GitHub’s repository page', place: 'github' },
  { name: 'The README on GitHub', place: 'readme' },
  { name: 'The site’s card in a link', place: 'card' }
]

/**
 * How long each place shows before the widget folds to the next, in
 * milliseconds.
 */
export const BEAT = 2400

/**
 * Reads the owner and the name of the repository at `repository`, a GitHub
 * address such as `https://github.com/owner/name`.
 */
export function repositoryOf(repository: string): { name: string, owner: string } {
  const [owner = '', name = ''] = new URL(repository).pathname.split('/').filter(Boolean)
  return { name, owner }
}

/**
 * Lists the badges the README opens on, the least Python the package accepts,
 * the coverage its suite is held to, and the site's host, as the facts about
 * `project` read them.
 */
export function badgesOf(project: Project): Badge[] {
  return [
    { name: 'Python', value: `${project.python}+` },
    { name: 'Coverage', value: `${project.gate}%` },
    { name: 'Docs', value: project.host }
  ]
}

/**
 * Holds the place the widget at `box` shows, folding to the next a beat after
 * the last while the widget shows and motion plays, and holding while a mouse
 * rests on the widget or a tab holds focus, the opening place, a place a
 * reader picks, and the place standing as a hold lets go each standing a full
 * beat.
 *
 * Returns:
 *   The place shown, the tabs as a group of options, and the listeners the
 *   widget takes.
 */
export function usePlaces(box: Ref<HTMLElement | undefined>) {
  const values = PLACES.map(each => each.place)
  const at     = ref<Place>(values[0]!)
  const opened = ref(false)
  const play   = useAutoplay(box, {
    beat   : BEAT,
    done   : () => false,
    finish : () => { opened.value = true },
    tick   : () => {
      if (opened.value) at.value = values[(values.indexOf(at.value) + 1) % values.length]!
      opened.value = true
    }
  })
  const release = (reason: 'keys' | 'pointer') => {
    opened.value = false
    play.hold(reason, false)
  }

  return {
    at        : at,
    listeners : {
      onFocusin      : () => play.hold('keys', true),
      onFocusout     : () => release('keys'),
      onPointerenter : (event: PointerEvent) => { if (fromMouse(event)) play.hold('pointer', true) },
      onPointerleave : (event: PointerEvent) => { if (fromMouse(event)) release('pointer') }
    },
    tabs      : useChoice(values, () => { opened.value = false }, at)
  }
}
