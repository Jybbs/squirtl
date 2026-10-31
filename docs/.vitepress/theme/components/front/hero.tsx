import { useData }                 from 'vitepress'
import { defineComponent, inject } from 'vue'

import { stageKey }    from '../../../lib/front/hero.ts'
import { logoLetters } from '../../../lib/marks/logo.ts'

/**
 * The front page's name, its tagline, and its byline in the hero's own slot,
 * the name in the display face with the R and the L Blue walks through in the
 * link color, each character a part the mark's flight sets its dots on.
 */
export const HeroName = defineComponent({
  name  : 'HeroName',
  setup : () => {
    const stage           = inject(stageKey, null)
    const { frontmatter } = useData()

    return () => {
      const { name, tagline, text } = frontmatter.value.hero as Record<'name' | 'tagline' | 'text', string>

      return (
        <div class="grid gap-4 text-left" ref={stage?.copy}>
          <h1 class="grid gap-3">
            <span class="font-display text-hero leading-tight font-medium text-ink">
              <span class="visually-hidden">{name}</span>
              <span aria-hidden="true">
                <span class="inline-block size-0" data-start />
                {Array.from(name, char => (
                  <span class={logoLetters.includes(char) ? 'text-link' : undefined} data-glyph>{char}</span>
                ))}
              </span>
            </span>
            <span class="font-display text-title leading-tight font-medium text-ink" data-rise>{text}</span>
          </h1>
          <span class="text-say text-quiet" data-rise>{tagline}</span>
        </div>
      )
    }
  }
})
