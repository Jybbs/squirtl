import { useData, useRoute, withBase }      from 'vitepress'
import { type VNode, defineComponent, ref } from 'vue'

import type { Edition }   from '../../../lib/cards/cards.ts'
import type { SiteTheme } from '../../../lib/config/navigation.ts'
import { SCREEN }         from '../../../lib/game/screen.ts'
import { NOT_FOUND }      from '../../../lib/missing/page.ts'
import { useGlitchCity }  from '../../../lib/missing/screen.ts'
import * as stops         from '../../../lib/missing/stops.ts'
import { HUES }           from '../kit/hues.ts'
import * as widget        from '../kit/widget.ts'

/**
 * The classes of a card's drawing, which scale the card to its column inside a
 * hairline in the rule that takes the card's hue under a pointer.
 */
const ART = 'block overflow-hidden rounded-2 border-hairline border-rule group-hover:border-current '
          + '*:block *:h-auto *:w-full'

/**
 * The classes of the round tile a section's badge sits in beside its label.
 */
const BADGE = 'grid size-mark place-items-center rounded-full *:size-mark-art *:pixelated'

/**
 * What a screen reader reads for the drawing of the Glitch City.
 */
const CITY_LABEL = 'Blue alone in a Glitch City built from Pallet Town’s own blocks in the wrong places, '
                 + 'spinning in place and up off the screen as Teleport takes him, then spinning back down '
                 + 'into the same place, the game’s text box at the foot reading AREA UNKNOWN'

/**
 * Draws the way back to `stop` as the card a shared link to its page shows, the
 * front page's card for the front page and the section's card for a section,
 * beneath which its mark and its label sit in its hue above its line.
 */
function cardOf(stop: stops.Stop, edition: Edition): VNode {
  const hue = stop.section ? HUES[stop.section.hue].text : 'text-link'
  return (
    <li class={['grid min-w-0 content-start gap-1', hue]} key={stop.link}>
      <a class="group focus-ring grid gap-2 rounded-1 no-underline" href={withBase(stop.link)}>
        <span aria-hidden="true" class={ART} innerHTML={stops.cardOf(stop, edition)} />
        <span class="flex min-w-0 items-center gap-2">
          {markOf(stop)}
          <span class="font-display text-body leading-tight font-medium group-hover:underline">
            {stop.label}
          </span>
        </span>
      </a>
      <span class="text-small leading-snug text-quiet">{stop.note}</span>
    </li>
  )
}

/**
 * Draws the mark beside `stop`'s label, Blue in his block for the front page
 * and the section's badge in a round tile of its hue for a section.
 */
function markOf(stop: stops.Stop): VNode {
  const { section } = stop
  const tile        = section ? [BADGE, HUES[section.hue].ground] : 'size-mark *:size-full'
  return <span aria-hidden="true" class={tile} innerHTML={stops.markOf(stop)} />
}

/**
 * The page a reader meets at an address the site carries no page for: Blue
 * alone in the Glitch City the address's own bytes read as, spinning off the
 * screen and back as Teleport takes him, beside the page's title, its one line
 * on what happened, the address asked for, and the way back as a card for the
 * front page and for each section in its hue.
 */
export const NotFound = defineComponent({
  name  : 'NotFound',
  setup : () => {
    const { theme } = useData<SiteTheme>()
    const route     = useRoute()
    const canvas    = ref<HTMLCanvasElement>()
    const address   = () => `${theme.value.edition.host}${route.path}`
    const ways      = stops.stopsOf()

    useGlitchCity(canvas, address)

    return () => (
      <div class="not-found grid justify-items-center px-5 py-7 lg:p-7">
        <div class="grid w-full max-w-missing-page items-center gap-6 lg:grid-cols-2">
          <canvas
            aria-label={CITY_LABEL}
            class={[widget.GAME_VIEW, 'max-w-missing-screen']}
            height={SCREEN.height}
            ref={canvas}
            role="img"
            width={SCREEN.width}
          />
          <div class="grid min-w-0 gap-4">
            <h1 class="m-0 font-display text-title leading-tight font-medium">{NOT_FOUND.title}</h1>
            <p class="m-0 text-say leading-normal">{NOT_FOUND.lead}</p>
            <p class="m-0 flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span class={widget.LABEL}>The address</span>
              <code class="font-code text-small wrap-anywhere">{address()}</code>
            </p>
            <ul class="m-0 mt-2 grid list-none grid-cols-2 gap-x-4 gap-y-5 p-0">
              {ways.map(stop => cardOf(stop, theme.value.edition))}
            </ul>
          </div>
        </div>
      </div>
    )
  }
})
