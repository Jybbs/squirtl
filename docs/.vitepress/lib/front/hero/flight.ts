import { type MaybeElementRef, tryOnScopeDispose, useIntersectionObserver, useTimeoutFn } from '@vueuse/core'
import { type Ref, inject, nextTick, ref, watch }                                         from 'vue'

import { IDENTITY }    from '../../identity/identity.ts'
import * as logo       from '../../marks/logo.ts'
import { useAutoplay } from '../../widgets/autoplay.ts'
import { useMotion }   from '../../widgets/motion.ts'
import * as hero       from '../hero.ts'

/**
 * How long Blue holds each frame as he walks in place in the mark, in
 * milliseconds.
 */
const STEP = 420

/**
 * The mark beside the hero's copy, the R and the L alone.
 */
export const artMark = logo.markOf(logo.logoLetters)

/**
 * The whole name as the mark, which flies apart into the typeset name and the
 * mark beside it.
 */
export const nameMark = logo.markOf(IDENTITY.name)

/**
 * The dots of the name's trail, from Blue's first step to his last.
 */
const nameTrail = nameMark.dots.filter((dot): dot is Extract<logo.Dot, { kind: 'trail' }> =>
  dot.kind === 'trail')

/**
 * When each part of the flight plays for the name's trail.
 */
const namePlan = hero.flightPlanOf(nameTrail.length)

/**
 * Reads every element `selector` matches inside `within`.
 */
const all = <T extends Element>(within: ParentNode, selector: string): T[] =>
  [...within.querySelectorAll<T>(selector)]

/**
 * Fills the trail of the name drawn in `flight` from the ground ahead to its
 * thirds a step at a time, fades the dot still ahead in, and drops the Poké
 * Ball onto the trail's end as it fills.
 */
function fillTrail(flight: SVGSVGElement): Animation[] {
  const { ahead, ball } = hero.PACE

  return [
    ...nameTrail.map(dot => flight.querySelector(`[data-step='${dot.step}']`)!.animate(
      [{ fill: 'var(--color-ahead)' }, { fill: `var(--color-${logo.toneOf(dot)})` }],
      { ...namePlan.fill(dot.step), easing: hero.CURVES.settle, fill: 'both' }
    )),
    ...all(flight, '[data-ahead]').map(dot => dot.animate(
      [{ opacity: ahead.from }, { opacity: 1 }],
      { ...namePlan.ahead, fill: 'backwards' }
    )),
    ...all(flight, '[data-ball]').map(each => each.animate([
      { opacity: 0, transform: `translateY(${-ball.drop}px)` },
      { offset: 0.5, opacity: 1, transform: 'translateY(0)' },
      { offset: 0.72, opacity: 1, transform: `translateY(${-ball.bounce}px)` },
      { opacity: 1, transform: 'translateY(0)' }
    ], { ...namePlan.ball, easing: hero.CURVES.drop, fill: 'backwards' }))
  ]
}

/**
 * Flies each character of the name drawn in `flight` apart, every letter Blue
 * does not walk through onto its place in the typeset name `typed` leads to,
 * shrinking its dots and fading them once the name is set, and the R and the L
 * onto the mark `to` draws.
 */
function flyLetters(flight: SVGSVGElement, from: hero.Drawn, to: hero.Drawn, typed: string): Animation[] {
  const { fly, settle } = hero.CURVES
  const { shrink }      = hero.PACE
  const ink             = all<SVGGElement>(flight, '[data-ink]')
  const walking         = all<SVGGElement>(flight, '[data-walk]')
  const still           = 'translate(0px, 0px) scale(1)'

  return [
    ...ink.map(group => group.animate(
      [{ transform: still }, { transform: typed }],
      { ...namePlan.ink(Number(group.dataset.letter)), easing: fly, fill: 'forwards' }
    )),
    ...all<SVGCircleElement>(flight, '[data-ink] circle').map(circle => circle.animate(
      [{ r: logo.dotRadius }, { offset: shrink.hold, r: logo.dotRadius }, { r: shrink.radius }],
      { ...namePlan.shrink, easing: fly, fill: 'forwards' }
    )),
    ...ink.map(group => group.animate(
      [{ opacity: 1 }, { opacity: 0 }],
      { ...namePlan.vanish, easing: settle, fill: 'forwards' }
    )),
    ...walking.map(group => {
      const onto = logo.logoLetters.indexOf(group.dataset.walk!)
      const left = nameMark.lefts[Number(group.dataset.letter)]!
      const end  = hero.flightTo(from, to, left, artMark.lefts[onto]!)
      return group.animate(
        [{ transform: still }, { transform: end }],
        { ...namePlan.walk(onto), easing: fly, fill: 'forwards' }
      )
    })
  ]
}

/**
 * Starts every part of the flight from the whole name drawn in `flight` onto
 * the typeset name in `copy`, the lines of `rest` beneath it, and the mark
 * drawn in `art`.
 *
 * Returns:
 *   The animations the flight plays, which landing cancels.
 */
function launch(
  art    : SVGSVGElement,
  copy   : HTMLElement,
  flight : SVGSVGElement,
  rest   : readonly HTMLElement[]
): Animation[] {
  const from   = { box: flight.getBoundingClientRect(), view: nameMark.view }
  const to     = { box: art.getBoundingClientRect(), view: artMark.view }
  const start  = copy.querySelector('[data-start]')!
  const size   = Number(getComputedStyle(start).fontSize.replace('px', ''))
  const origin = hero.originOf(start.getBoundingClientRect(), size)

  return [
    ...flyLetters(flight, from, to, hero.toType(from, nameMark.baseline, origin)),
    ...fillTrail(flight),
    ...typeIn(copy, rest)
  ]
}

/**
 * Fades each typeset character of `copy` in and raises each line of `rest` into
 * place beneath it.
 */
function typeIn(copy: HTMLElement, rest: readonly HTMLElement[]): Animation[] {
  const { settle } = hero.CURVES

  return [
    ...all<HTMLElement>(copy, '[data-glyph]').map((glyph, index) => glyph.animate(
      [{ opacity: 0 }, { opacity: 1 }],
      { ...namePlan.glyph(index), easing: settle, fill: 'both' }
    )),
    ...rest.map((part, index) => part.animate(
      [{ opacity: 0, transform: `translateY(${hero.PACE.rise.lift}px)` }, { opacity: 1, transform: 'none' }],
      { ...namePlan.rise(index), easing: settle, fill: 'both' }
    ))
  ]
}

/**
 * Flies the whole name drawn in the overlay `flight` holds apart onto the copy
 * the hero's stage holds and the mark `art` holds, each time `art` comes into
 * view with motion playing, landing at the flight's end and at once where `art`
 * leaves the view or motion stops.
 *
 * Returns:
 *   Whether the name is flying, during which the overlay shows and the mark
 *   beside the copy hides.
 */
export function useFlight(
  art    : Ref<HTMLElement | undefined>,
  flight : Ref<HTMLElement | undefined>,
  host   : Ref<HTMLElement | undefined>
): Ref<boolean> {
  const stage              = inject(hero.stageKey, null)
  const animate            = useMotion()
  const flying             = ref(false)
  let playing: Animation[] = []
  let flown                = 0

  const land = () => {
    flown += 1
    landing.stop()
    for (const animation of playing) animation.cancel()
    playing      = []
    flying.value = false
  }

  const landing = useTimeoutFn(land, namePlan.done, { immediate: false })

  const lift = async () => {
    land()
    const id = flown
    await document.fonts.ready
    const copy = stage?.copy.value
    if (id !== flown || !copy || !host.value) return
    flying.value = true
    await nextTick()
    const rest = [...all<HTMLElement>(copy, '[data-rise]'), ...all<HTMLElement>(host.value, '.actions')]
    playing = launch(art.value!.querySelector('svg')!, copy, flight.value!.querySelector('svg')!, rest)
    landing.start()
  }

  useIntersectionObserver(art, ([entry]) => {
    if (entry?.isIntersecting && animate.value) void lift()
    else land()
  })
  watch(animate, land)
  tryOnScopeDispose(land)

  return flying
}

/**
 * Walks Blue in place in the mark at `art` while it shows on screen with motion
 * playing, switching between his walking frame and his standing one every
 * step, and leaves him on his walking frame where motion is off.
 *
 * Returns:
 *   Whether Blue shows his standing frame.
 */
export function useStanding(art: MaybeElementRef): Ref<boolean> {
  const standing = ref(false)

  useAutoplay(art, {
    beat   : STEP,
    done   : () => false,
    finish : () => { standing.value = false },
    tick   : () => { standing.value = !standing.value }
  })

  return standing
}
