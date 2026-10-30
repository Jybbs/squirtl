import { Teleport, defineComponent, onMounted, ref } from 'vue'

import * as flight     from '../../../lib/front/hero/flight.ts'
import { IDENTITY }    from '../../../lib/identity/identity.ts'
import { logoLetters } from '../../../lib/marks/logo.ts'
import { drawMark }    from './mark/logo.tsx'

/**
 * The mark in the front page's hero, the R and the L with Blue walking in place
 * in each. As the hero comes into view with motion playing, the whole name
 * flies apart over the hero, its letters setting into the typeset name and its
 * R and L into this mark, while the trail fills and the Poké Ball drops onto
 * its end.
 */
export const HeroMark = defineComponent({
  name  : 'HeroMark',
  setup : () => {
    const art      = ref<HTMLElement>()
    const host     = ref<HTMLElement>()
    const overlay  = ref<HTMLElement>()
    const flying   = flight.useFlight(art, overlay, host)
    const standing = flight.useStanding(art)

    onMounted(() => {
      host.value = art.value!.closest<HTMLElement>('.VPHero > .container') ?? undefined
    })

    return () => (
      <div
        aria-label={`The ${[...logoLetters].join(' and the ')} of the ${IDENTITY.name} logo`}
        class={['w-full', flying.value && 'opacity-0']}
        ref={art}
        role="img"
      >
        {drawMark(flight.artMark, standing.value)}
        {host.value && (
          <Teleport to={host.value}>
            <div
              aria-hidden="true"
              class={[
                'pointer-events-none absolute inset-0 z-20 items-center px-5 py-6',
                flying.value ? 'flex' : 'hidden'
              ]}
              ref={overlay}
            >
              <div class="mx-auto w-full max-w-hero-flight">{drawMark(flight.nameMark)}</div>
            </div>
          </Teleport>
        )}
      </div>
    )
  }
})
