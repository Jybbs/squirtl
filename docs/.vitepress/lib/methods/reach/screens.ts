import { type Ref, onMounted, watch } from 'vue'

import { type Faded, fadedOf }   from '../../game/fades.ts'
import { RoomImages }            from '../../game/images.ts'
import * as reach                from '../reach.ts'
import { PALETTES, paintScreen } from './paint.ts'

/**
 * One screen of the walk, the learner it draws, its name beneath, what a screen
 * reader reads for it, the series it fills the pad's Up arm from, and whether
 * that series holds odds rather than values.
 */
export interface Screen {
  group  : string
  name   : string
  odds   : boolean
  says   : string
  series : keyof Omit<reach.Run, 'copied'>
}

/**
 * The screens abreast: the deep Q-network's online network and its copy, PQN's
 * one network, and PPO's odds.
 */
export const SCREENS: readonly Screen[] = [
  { group: 'Deep Q-network', name: 'Online', odds: false, says: 'the deep Q-network’s online network’s value of it', series: 'online' },
  { group: 'Deep Q-network', name: 'Copy', odds: false, says: 'the deep Q-network’s copy’s value of it', series: 'copy' },
  { group: 'PQN', name: 'No copy', odds: false, says: 'PQN’s value of it', series: 'pqn' },
  { group: 'PPO', name: 'Odds', odds: true, says: 'PPO’s odds of it', series: 'odds' }
]

/**
 * The learners over the screens, each with the screens it spans.
 */
export const GROUPS = [...new Set(SCREENS.map(each => each.group))].map(group => ({ group, span: SCREENS.filter(each => each.group === group).length }))

/**
 * Draws every screen into `canvases` as training stands at `moment`, the
 * values landed `landed` of the way and the copy `copied` of the way, once
 * Pallet Town's image loads.
 */
export function useScreens(canvases: Ref<HTMLCanvasElement[]>, moment: Ref<reach.Moment>, landed: Ref<number>, copied: Ref<number>): void {
  const images = new RoomImages()
  let faded: Faded | null = null

  const paint = () => {
    canvases.value.forEach((canvas, n) => {
      const context = canvas.getContext('2d')
      const screen  = SCREENS[n]!
      if (context) {
        const shared = screen.series === 'copy' ? copied.value : landed.value
        paintScreen(context, faded, { odds: screen.odds, values: reach.RUN[screen.series] }, shared, moment.value)
      }
    })
  }

  watch([moment, landed, copied], paint)
  onMounted(() => images.whenReady(() => {
    faded = fadedOf(images.image('pallet'), PALETTES)
    paint()
  }, ['pallet']))
}
