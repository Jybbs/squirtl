import { defaultDocument, useEventListener, useResizeObserver } from '@vueuse/core'
import { type Ref, onMounted, watch }                           from 'vue'

import { type Canvas, useCanvasLoop } from '../../widgets/frames.ts'
import { useMotion }                  from '../../widgets/motion.ts'
import * as sky                       from '../sky.ts'

/**
 * The parts of the front page the walks dim behind, the hero's words and each
 * part of the page's body, every section's whole block among them.
 */
const QUIET = '.VPHomeHero .main, .vp-doc > div > *'

/**
 * Reads the page's size, the viewport, and the regions the walks dim behind
 * into `scene`, and sizes `canvas` to the viewport at the device's pixel
 * ratio.
 *
 * Returns:
 *   The pixel ratio the canvas draws at, at most 2.
 */
function measureScene(canvas: HTMLCanvasElement, scene: sky.Scene, tuning: sky.Sky): number {
  const page    = document.documentElement
  const ratio   = Math.min(2, window.devicePixelRatio)
  const quiet   = Array.from(document.querySelectorAll(QUIET), part => part.getBoundingClientRect())
  scene.width   = page.clientWidth
  scene.view    = window.innerHeight
  scene.height  = page.scrollHeight
  scene.scroll  = window.scrollY
  scene.quiet   = sky.quietOf(quiet, scene.scroll, tuning)
  canvas.width  = Math.round(scene.width * ratio)
  canvas.height = Math.round(scene.view * ratio)
  return ratio
}

/**
 * Draws the splash into `canvas` in the tones `dark` picks: the reader's walk
 * down the page as they scroll, with motion playing, and the whole walk still
 * without it, drawn again as the page resizes, the reader scrolls, or the
 * scheme changes.
 */
export function useSky(canvas: Canvas, dark: Ref<boolean>, tuning: sky.Sky = sky.SKY): void {
  const animate              = useMotion()
  const scene: sky.Scene     = { height: 0, quiet: [], scroll: 0, still: true, time: 0, view: 0, width: 0 }
  let branches: sky.Branch[] = []
  let head                   = 0
  let ratio                  = 1
  let walk: sky.SkyPoint[]   = []

  const { paint } = useCanvasLoop(canvas, {
    advance: elapsed => {
      scene.time += elapsed / 1000
      head += (sky.headOf(walk, scene, tuning) - head) * Math.min(1, elapsed / 1000 * tuning.follow)
      return true
    },

    draw: context => {
      if (!scene.width) return
      scene.still = !animate.value
      context.setTransform(ratio, 0, 0, ratio, 0, 0)
      context.clearRect(0, 0, scene.width, scene.view)
      sky.paintSky(context, branches, head, scene, sky.TONES[dark.value ? 'dark' : 'light'], walk, tuning)
    }
  })

  const measure = () => {
    ratio    = measureScene(canvas.value!, scene, tuning)
    walk     = sky.serpentine(scene.width, scene.height, tuning)
    branches = sky.branchesOf(walk, scene.width, tuning)
    head     = sky.headOf(walk, scene, tuning)
    paint()
  }

  onMounted(measure)
  useResizeObserver(defaultDocument?.body, measure)
  useEventListener('scroll', () => {
    scene.scroll = window.scrollY
    if (!animate.value) paint()
  }, { passive: true })
  watch([dark, animate], paint)
}
