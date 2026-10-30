import { useData }         from 'vitepress'
import { defineComponent } from 'vue'

import { sectionOf }   from '../../../lib/config/sections.ts'
import { badgeMarkup } from '../../../lib/drawing/badges.ts'
import { Chip }        from '../kit/chip.tsx'
import { HUES }        from '../kit/hues.ts'

/**
 * The marks of the section a page sits in, set before its title: a ribbon in
 * the section's hue hanging from the top of the column with the section's badge
 * in a round tile at its tail, and the chip naming the section over the title,
 * both left out of a page no section holds.
 */
export const SectionMark = defineComponent({
  name  : 'SectionMark',
  setup : () => {
    const { page } = useData()

    return () => {
      const section = sectionOf(page.value)
      if (!section) return null
      const badge = badgeMarkup(section.badge, section.hue)

      return (
        <div class="section-mark mb-4">
          <div
            aria-hidden="true"
            class={[
              'section-ribbon absolute top-0 right-4 grid h-ribbon-short w-ribbon-narrow items-end '
              + 'justify-items-center pb-ribbon-tail-narrow',
              'sm:right-5 sm:h-ribbon-long sm:w-ribbon sm:pb-ribbon-tail',
              HUES[section.hue].badge
            ]}
          >
            <span
              class={[
                'section-badge grid size-ribbon-circle-narrow place-items-center rounded-full border-ring '
                + 'border-ground *:size-mark *:pixelated sm:size-ribbon-circle',
                HUES[section.hue].ground
              ]}
              innerHTML={badge}
            />
          </div>
          <Chip hue={section.hue} mark={badge} name={section.name} />
        </div>
      )
    }
  }
})
