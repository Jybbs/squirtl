import type { MaybeElementRef }                                        from '@vueuse/core'
import { type ComputedRef, type Ref, computed, onMounted, ref, watch } from 'vue'

import { RoomImages }                                from '../../game/images.ts'
import { type Canvas, type Painting, useCanvasLoop } from '../../widgets/frames.ts'
import { type Playback, useScrub }                   from '../../widgets/scrub.ts'
import { clockText }                                 from '../learning.ts'
import * as transition                               from './transition.ts'
import type { Walks }                                from './walks.ts'

/**
 * The walk picked out, the one a mouse points at or else the one pressed,
 * beside the one pressed and the calls that point at a walk and press one.
 */
export interface Picking {
  hover  : (walk: number | null) => void
  picked : ComputedRef<number | null>
  pin    : (walk: number) => void
  pinned : Ref<number | null>
}

/**
 * The name a screen reader reads for the clock the strip controls.
 */
const SLIDER = 'The clock of presses every walk shares, which holds every walk at the press it points to'

/**
 * Picks out the Blue of the walk a mouse points at, or else of the walk
 * pressed, drawing the pick onto the town through `painting` as it changes, a
 * second press of the pressed walk letting it go.
 */
export function usePicking(painting: Painting, walks: Walks): Picking {
  const hovered = ref<number | null>(null)
  const pinned  = ref<number | null>(null)
  const picked  = computed(() => hovered.value ?? pinned.value)

  watch(picked, focus => {
    walks.focus = focus
    painting.paint()
  })

  return {
    hover  : walk => { hovered.value = walk },
    picked : picked,
    pin    : walk => { pinned.value = pinned.value === walk ? null : walk },
    pinned : pinned
  }
}

/**
 * Plays `walks` a press at a time while the widget at `root` shows on screen,
 * ending each loop in the transition into a wild battle, and makes the strip a
 * slider over the clock that holds the play while a reader points at it or
 * moves it with the keys.
 */
export function usePlayback(painting: Painting, root: MaybeElementRef, walks: Walks): Playback {
  const at    = ref(0)
  let closing = false

  const seek = (press: number) => {
    closing = false
    walks.calm()
    walks.set(press)
    at.value = press
    painting.paint()
  }

  const scrub = useScrub(root, {
    beat   : () => closing ? transition.TRANSITION.frame : walks.play.press,
    done   : () => at.value >= walks.longest && !closing,
    finish : () => seek(walks.longest),

    restart: () => {
      closing = true
      walks.encounter(() => {
        walks.set(0)
        at.value = 0
      })
      painting.wake()
    },

    tick: () => {
      if (closing) {
        closing = walks.closing
        return
      }
      walks.set(at.value + 1, walks.play.press)
      at.value++
      painting.wake()
    }
  }, {
    at       : at,
    count    : walks.longest + 1,
    describe : press => clockText(walks.moments, press),
    label    : SLIDER,
    seek     : seek
  })

  return { at, scrub }
}

/**
 * Draws `walks` onto `canvas` once Pallet Town's image can draw, through
 * `paint` at once and on every frame while something moves once `wake` starts
 * the loop, and draws nothing where the image fails to decode.
 */
export function useTownCanvas(canvas: Canvas, walks: Walks): Painting {
  const images = new RoomImages()
  let town: transition.Town | undefined

  const painting = useCanvasLoop(canvas, {
    advance : elapsed => walks.advance(elapsed),
    draw    : context => { if (town) walks.draw(context, town) }
  })

  onMounted(() => images.whenReady(() => {
    const context = canvas.value?.getContext('2d')
    if (!context) return
    town = transition.townFrom(context, images.image('pallet'), walks.view)
    painting.paint()
  }, ['pallet']))

  return painting
}
