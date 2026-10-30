import { describe, expect, it } from 'vitest'

import * as hero from '../../../lib/front/hero.ts'

/**
 * The whole name drawn 1,860 pixels wide at the viewport's top left, half a
 * pixel to each unit of the mark's frame.
 */
const NAME: hero.Drawn = { box: { left: 0, top: 0, width: 1860 }, view: { width: 3720, x: -10, y: -10 } }

/**
 * Reads the offset and the scale a transform `flightTo` or `toType` writes.
 */
const parts = (transform: string): number[] => transform.match(/-?[\d.]+(?=px|\))/gu)!.map(Number)

/**
 * Reads where a point at `units` along one axis of the whole name's frame,
 * whose edge sits at `origin`, falls on the screen.
 */
const onScreen = (units: number, origin: number): number =>
  (units - origin) * NAME.box.width / NAME.view.width

describe('flightTo', () => {
  it('carries a letter onto a drawing of its own size at the same place unmoved', () => {
    expect(parts(hero.flightTo(NAME, NAME, 600, 600))).toStrictEqual([0, 0, 1])
  })

  it('scales a letter to the other drawing, landing its left and its top where that one sets them', () => {
    const art: hero.Drawn = { box: { left: 200, top: 100, width: 255 }, view: { width: 1020, x: -10, y: 90 } }
    const [x, y, scale] = parts(hero.flightTo(NAME, art, 3300, 600))

    expect([scale, onScreen(3300 * scale! + x!, NAME.view.x), onScreen(90 * scale! + y!, NAME.view.y)])
      .toStrictEqual([0.5, 200 + (600 - art.view.x) / 4, 100])
  })
})

describe('originOf', () => {
  it('places the name on its start’s baseline, a unit of the face a thousandth of its size', () => {
    expect(hero.originOf({ left: 40, top: 120 }, 44)).toStrictEqual({ baseline: 120, left: 40, unit: 0.044 })
  })
})

describe('flightPlanOf', () => {
  const plan = hero.flightPlanOf(26)

  it.each([
    ['ink', 0, { delay: 420, duration: 1200 }],
    ['ink', 6, { delay: 840, duration: 1200 }],
    ['walk', 1, { delay: 650, duration: 1450 }],
    ['fill', 0, { delay: 940, duration: 260 }],
    ['fill', 25, { delay: 2090, duration: 260 }],
    ['glyph', 2, { delay: 1350, duration: 420 }],
    ['rise', 1, { delay: 1230, duration: 760 }]
  ] as const)('starts %s %i at the step the take sets', (part, index, timing) => {
    expect(plan[part](index)).toStrictEqual(timing)
  })

  it('fades the dot ahead in as the trail fills, drops the ball before, and ends once both settle', () => {
    expect([plan.ahead, plan.ball, plan.shrink, plan.vanish, plan.done]).toStrictEqual([
      { delay: 2136, duration: 300 },
      { delay: 1756, duration: 820 },
      { delay: 420, duration: 1350 },
      { delay: 1350, duration: 360 },
      2656
    ])
  })

  it('ends at the letters’ landing where the trail is short', () => {
    expect(hero.flightPlanOf(1).done).toBe(420 + 1350 + 450)
  })
})

describe('toType', () => {
  it('lays the mark’s baseline on the name’s and scales each cell of the mark to the face’s', () => {
    const [x, y, scale] = parts(hero.toType(NAME, 700, { baseline: 300, left: 50, unit: 0.044 }))

    expect([x, scale]).toStrictEqual([90, 0.088])
    expect((700 * scale! + y! - NAME.view.y) / 2).toBeCloseTo(300)
  })
})
