import { clamp, useElementSize }           from '@vueuse/core'
import { type Ref, onMounted, ref, watch } from 'vue'

import type { RoomImages }       from '../../game/images.ts'
import { IDENTITY }              from '../../identity/identity.ts'
import { still }                 from '../../widgets/still.ts'
import { type Segment, along }   from '../curriculum.ts'
import { type Lane, LaneScreen } from './screens.ts'

/**
 * What one lane shows: the episode standing at `start` in segment `segment`,
 * the screen at `lane`, and the words `far` beside it.
 */
export interface Showing {
  far     : string
  images  : RoomImages
  lane    : Lane
  segment : Segment
  start   : number
}

/**
 * The elements of one lane the layout moves: the gray and Denim stretches, the
 * screen's canvas, the far figure, the screen, and the track holding them.
 */
export interface Parts {
  after  : Ref<HTMLElement | undefined>
  before : Ref<HTMLElement | undefined>
  canvas : Ref<HTMLCanvasElement | undefined>
  far    : Ref<HTMLElement | undefined>
  screen : Ref<HTMLElement | undefined>
  track  : Ref<HTMLElement | undefined>
}

/**
 * Where the parts of one lane stand along its track, in pixels from its left:
 * the start, where the gray stretch from the bedroom ends and the Denim stretch
 * to the goal begins, the far figure's left, the Denim stretch's width, the
 * screen's left edge, and the side of the screen the far figure stands on.
 */
export interface Placement {
  at     : number
  far    : number
  reach  : number
  screen : number
  side   : Side
}

/**
 * The sizes a lane is laid out from, in pixels: its track's width, its
 * screen's, its far figure's, and the gap between the screen and the figure.
 */
export interface Sizes {
  far    : number
  screen : number
  track  : number
  gap?   : number
}

/**
 * A side of a lane's screen.
 */
export type Side = 'left' | 'right'

/**
 * Lays one lane out with its episode starting at step `start` toward a goal a
 * step past `end`: the screen centered on the start where the track allows, the
 * gray stretch up to the start and the Denim stretch on to the goal, and the
 * far figure beside the screen on `side` while it fits there, on the right
 * where it fits and on the left otherwise, so it changes sides only where the
 * screen leaves it no room.
 */
export function placeOf(sizes: Sizes, start: number, end: number, side: Side): Placement {
  const { far, gap = IDENTITY.lengths.spacing['2'], screen, track } = sizes
  const at     = along(start) * track
  const left   = clamp(at - screen / 2, 0, track - screen)
  const room   = { left: left >= far + gap, right: track - left - screen >= far + gap }
  const placed = room[side] ? side : room.right ? 'right' : 'left'
  return {
    at     : at,
    far    : placed === 'right' ? left + screen + gap : left - gap - far,
    reach  : Math.max(0, along(end + 1) * track - at),
    screen : left,
    side   : placed
  }
}

/**
 * Lays one lane out and draws its screen: the screen, the stretches, and the
 * far figure glide to each new start, land at once on a new width or where the
 * figure changes sides, and the canvas draws the recording at each step once
 * the rooms load.
 */
export function useLane(showing: Showing): Parts {
  const parts: Parts = { after: ref(), before: ref(), canvas: ref(), far: ref(), screen: ref(), track: ref() }
  const view         = new LaneScreen(showing.segment, showing.images)
  const { width }    = useElementSize(parts.track)
  let side: Side     = 'right'
  let placed         = false

  const draw = () => {
    const context = parts.canvas.value?.getContext('2d')
    if (context) view.draw(context, showing.lane.step)
  }

  const place = () => {
    const [after, before, far, screen] = [parts.after.value!, parts.before.value!, parts.far.value!, parts.screen.value!]
    const at    = placeOf({ far: far.offsetWidth, screen: screen.offsetWidth, track: width.value }, showing.start, showing.segment.end, side)
    const apply = () => {
      before.style.width     = `${at.at}px`
      after.style.transform  = `translateX(${at.at}px)`
      after.style.width      = `${at.reach}px`
      screen.style.transform = `translateX(${at.screen}px)`
      far.style.transform    = `translateX(${at.far}px)`
    }
    if (placed && at.side === side) apply()
    else still([after, before, far, screen], apply)
    placed = true
    side   = at.side
  }

  watch(() => showing.lane.step, draw)
  watch([() => showing.start, () => showing.far], place, { flush: 'post' })
  watch(width, () => {
    placed = false
    place()
  }, { flush: 'post' })
  onMounted(() => showing.images.whenReady(draw))
  return parts
}
