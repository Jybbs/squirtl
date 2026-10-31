import DefaultTheme                                from 'vitepress/theme-without-fonts'
import { defineComponent, h, provide, shallowRef } from 'vue'

import { stageKey }    from '../lib/front/hero.ts'
import { HeroName }    from './components/front/hero.tsx'
import { HeroMark }    from './components/front/mark.tsx'
import { Splash }      from './components/front/splash.tsx'
import { NotFound }    from './components/missing/not-found.tsx'
import { SectionMark } from './components/section/ribbon.tsx'

/**
 * The default theme's layout with the site's own parts in its slots, the marks
 * of a page's section over its title, the hero's name and mark on the front
 * page and the splash behind it, sharing the stage the mark's flight lands the
 * name on, and the page a reader meets at a missing address.
 */
export const Layout = defineComponent({
  name  : 'Layout',
  setup : () => {
    provide(stageKey, { copy: shallowRef<HTMLElement | null>(null) })

    return () => h(DefaultTheme.Layout, null, {
      'doc-before'       : () => h(SectionMark),
      'home-hero-before' : () => h(Splash),
      'home-hero-image'  : () => h(HeroMark),
      'home-hero-info'   : () => h(HeroName),
      'not-found'        : () => h(NotFound)
    })
  }
})
