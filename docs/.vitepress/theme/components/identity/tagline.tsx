import { useData }              from 'vitepress'
import { defineComponent, ref } from 'vue'

import type { SiteTheme }      from '../../../lib/config/navigation.ts'
import { PLACES, usePlaces }   from '../../../lib/identity/places.ts'
import { drawPlace }           from './places.tsx'

/**
 * The tagline and the byline in each place a reader meets them, three folder
 * cards stacked with their tabs offset, GitHub's repository page with the
 * byline in its About box beside the keywords, the site's front page with the
 * tagline beneath the name, and the site's card in a link, the stack folding
 * from one to the next until a reader points at it or picks a tab.
 */
export const IdentityTagline = defineComponent({
  name  : 'IdentityTagline',
  setup : () => {
    const { isDark, theme } = useData<SiteTheme>()
    const box               = ref<HTMLElement>()
    const { at, listeners, tabs } = usePlaces(box)

    return () => (
      <div class="identity-folders @container grid" ref={box} {...listeners}>
        <div {...tabs.root.value} aria-label="The places" class="identity-fan grid">
          {PLACES.map(({ name, place }, n) => {
            const depth = (n - PLACES.findIndex(each => each.place === at.value) + PLACES.length) % PLACES.length
            return (
              <figure aria-label={name} class="identity-folder relative m-0 grid rounded-3 bg-ground" data-depth={depth} style={{ '--tab': n }}>
                <button {...tabs.item(place)} class="identity-folder-tab focus-ring absolute cursor-pointer rounded-t-2 bg-ground px-3 py-2 text-left font-body text-small text-ink" type="button">
                  {name}
                </button>
                <div class="identity-folder-body overflow-hidden rounded-3" inert={depth !== 0}>{drawPlace(place, theme.value, isDark.value ? 'dark' : 'light')}</div>
              </figure>
            )
          })}
        </div>
      </div>
    )
  }
})
