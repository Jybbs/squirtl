import { useData }              from 'vitepress'
import { defineComponent, ref } from 'vue'

import { useSky } from '../../../lib/front/sky/splash.ts'

/**
 * The splash behind the front page, the reader's walk drawn down the page as
 * they scroll with side paths branching off it and fading, as an exploring
 * agent's do, the whole walk drawn still where the reader asks for reduced
 * motion.
 */
export const Splash = defineComponent({
  name  : 'Splash',
  setup : () => {
    const canvas = ref<HTMLCanvasElement>()
    useSky(canvas, useData().isDark)

    return () => (
      <canvas aria-hidden="true" class="pointer-events-none fixed inset-0 -z-1 size-full" ref={canvas} />
    )
  }
})
