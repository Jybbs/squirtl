import type { InjectionKey, ShallowRef } from 'vue'

import type { Mark } from '../marks/logo.ts'

/**
 * A drawing of the mark on the screen, the box it fills in CSS pixels from the
 * viewport's top left and the frame of the mark it is viewed through.
 */
export interface Drawn {
  box  : Pick<DOMRectReadOnly, 'left' | 'top' | 'width'>
  view : Pick<Mark['view'], 'width' | 'x' | 'y'>
}

/**
 * When each part of the flight plays, in milliseconds from its start:
 *
 * - `ahead`, the dot still ahead of Blue fading in once the trail fills
 * - `ball`, the Poké Ball dropping onto the end of the trail and bouncing
 * - `done`, the end of the whole flight
 * - `fill`, the trail dot at a step changing from the ground ahead to its
 *   third
 * - `glyph`, the typeset character at an index fading in
 * - `ink`, the dots of the character at an index flying to their place in
 *   the name
 * - `rise`, the copy beneath the name at an index rising into place
 * - `shrink`, every flying dot shrinking to the weight of the typeset name
 * - `vanish`, the flying dots fading once the name is set
 * - `walk`, the R or the L flying to the mark beside the name
 */
export interface FlightPlan {
  ahead  : Timing
  ball   : Timing
  done   : number
  fill   : (step: number) => Timing
  glyph  : (index: number) => Timing
  ink    : (index: number) => Timing
  rise   : (index: number) => Timing
  shrink : Timing
  vanish : Timing
  walk   : (index: number) => Timing
}

/**
 * Where the name sits once typeset, the left of its first character and its
 * baseline in CSS pixels from the viewport's top left, beside the pixels one
 * unit of the display face spans, a thousandth of the name's font size.
 */
export interface Origin {
  baseline : number
  left     : number
  unit     : number
}

/**
 * The part of the front page's hero that the name's slot fills, the copy the
 * mark's slot flies the name's dots onto, holding the typeset characters, a
 * point on the name's baseline where its first character starts, and the lines
 * beneath the name that rise in once it is set.
 */
export interface Stage {
  copy : ShallowRef<HTMLElement | null>
}

/**
 * One part of the flight, the wait before it plays and how long it plays for,
 * in milliseconds.
 */
interface Timing {
  delay    : number
  duration : number
}

/**
 * The curves the flight's parts move on, the dots and the letters flying on an
 * ease in and out, each part settling on an ease out, and the Poké Ball
 * dropping on an ease in.
 */
export const CURVES = {
  drop   : 'ease-in',
  fly    : 'cubic-bezier(0.65, 0, 0.35, 1)',
  settle : 'cubic-bezier(0.22, 1, 0.36, 1)'
} as const

/**
 * The units of the display face's em, in which each cell of the mark spans a
 * hundred.
 */
const EM = 1000

/**
 * The flight's pace, in milliseconds unless named otherwise, each part's
 * `duration` its length, `every` the stagger between two of its items, and
 * `wait` its delay after the dots lift off:
 *
 * - `ahead`, the dot still ahead's fade and the opacity it fades in from
 * - `ball`, the Poké Ball's drop, the heights in the mark's units it drops
 *   from and bounces to, and how long before the trail fills it starts
 * - `fill`, each trail dot's change of color
 * - `flight`, the wait before the dots lift off and the length of their
 *   flight
 * - `glyph`, each typeset character's fade and the share of the flight it
 *   waits for
 * - `ink`, each character's dots flying to the name
 * - `rise`, the copy's rise and the pixels it rises through
 * - `settle`, how long the flight runs past the dots' flight and past the
 *   trail's fill
 * - `shrink`, the radius in the mark's units the flying dots shrink to and
 *   the share of the flight they hold their own for
 * - `vanish`, the flying dots' fade and its wait after the typeset
 *   characters start fading in
 * - `walk`, the R's and the L's flight
 */
export const PACE = {
  ahead  : { duration: 300, from: 0.4 },
  ball   : { bounce: 38, drop: 240, duration: 820, lead: 380 },
  fill   : { duration: 260, every: 46, wait: 520 },
  flight : { duration: 1350, start: 420 },
  glyph  : { duration: 420, every: 60, share: 0.6 },
  ink    : { duration: 1200, every: 70 },
  rise   : { duration: 760, every: 110, lift: 14, wait: 700 },
  settle : { fill: 520, flight: 450 },
  shrink : { hold: 0.45, radius: 34 },
  vanish : { duration: 360, wait: 120 },
  walk   : { duration: 1450, every: 110, wait: 120 }
}

/**
 * The key the front page's layout provides the hero's stage under.
 */
export const stageKey: InjectionKey<Stage> = Symbol('stage')

/**
 * Reads when each part of the flight plays at `pace` for a trail of `trail`
 * dots, the trail filling once the letters have lifted off and the Poké Ball
 * landing as it ends.
 */
export function flightPlanOf(trail: number, pace: typeof PACE = PACE): FlightPlan {
  const { ahead, ball, fill, flight, glyph, ink, rise, settle, vanish, walk } = pace
  const fillAt = (step: number) => flight.start + fill.wait + step * fill.every
  const filled = fillAt(trail)
  const typed  = flight.start + flight.duration * glyph.share

  return {
    ahead  : { delay: filled, duration: ahead.duration },
    ball   : { delay: filled - ball.lead, duration: ball.duration },
    done   : Math.max(flight.start + flight.duration + settle.flight, filled + settle.fill),
    fill   : step => ({ delay: fillAt(step), duration: fill.duration }),
    glyph  : index => ({ delay: typed + index * glyph.every, duration: glyph.duration }),
    ink    : index => ({ delay: flight.start + index * ink.every, duration: ink.duration }),
    rise   : index => ({ delay: flight.start + rise.wait + index * rise.every, duration: rise.duration }),
    shrink : { delay: flight.start, duration: flight.duration },
    vanish : { delay: typed + vanish.wait, duration: vanish.duration },
    walk   : index => ({ delay: flight.start + walk.wait + index * walk.every, duration: walk.duration })
  }
}

/**
 * Writes the transform that carries the part of one drawing of the mark whose
 * letter starts at `left` onto the letter of another drawing starting at
 * `onto`, both in the mark's units, scaling it from the first drawing's size to
 * the second's.
 */
export function flightTo(from: Drawn, to: Drawn, left: number, onto: number): string {
  const scale = from.view.width / from.box.width
  const ratio = to.box.width / to.view.width * scale
  const x     = (to.box.left - from.box.left) * scale + from.view.x + (onto - to.view.x - left) * ratio
  const y     = (to.box.top - from.box.top) * scale + from.view.y - to.view.y * ratio

  return `translate(${x}px, ${y}px) scale(${ratio})`
}

/**
 * Places the typeset name from `start`, the box of a point on its baseline
 * where its first character starts, set at `size` pixels.
 */
export function originOf(start: Pick<DOMRectReadOnly, 'left' | 'top'>, size: number): Origin {
  return { baseline: start.top, left: start.left, unit: size / EM }
}

/**
 * Writes the transform that sets a drawing of the mark's characters onto the
 * typeset name at `origin`, scaling each cell of the mark to the cell of the
 * display face it draws and laying the mark's `baseline` on the name's.
 */
export function toType(from: Drawn, baseline: number, origin: Origin): string {
  const scale = from.view.width / from.box.width
  const ratio = origin.unit * scale
  const x     = (origin.left - from.box.left) * scale + from.view.x
  const y     = (origin.baseline - from.box.top) * scale + from.view.y - baseline * ratio

  return `translate(${x}px, ${y}px) scale(${ratio})`
}
