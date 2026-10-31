import { describe, expect, it } from 'vitest'

import * as plot from '../../../lib/drawing/plot.ts'

/**
 * A plot 200 pixels wide and 100 tall, leaving room on every side.
 */
const FRAME = plot.frameOf({ bottom: 20, left: 30, right: 10, top: 5 }, 100, 200)

describe('frameOf', () => {
  it('sets the floor above the bottom room and the right edge inside the right room', () => {
    expect([FRAME.end, FRAME.floor]).toStrictEqual([190, 80])
  })

  it.each([
    [0, 3, 30, 80],
    [1, 3, 83.3, 55],
    [3, 3, 190, 5]
  ])('places %s of %s at %s across and %s up, to a tenth of a pixel', (part, whole, x, y) => {
    expect([FRAME.x(part, whole), FRAME.y(part, whole)]).toStrictEqual([x, y])
  })
})

describe('multiplesOf', () => {
  it.each([
    [10, 35, [0, 10, 20, 30]],
    [10, 40, [0, 10, 20, 30, 40]],
    [25, 0, [0]]
  ])('lists every multiple of %s up to %s', (every, upTo, multiples) => {
    expect(plot.multiplesOf(every, upTo)).toStrictEqual(multiples)
  })
})

describe('round', () => {
  it.each([
    [12.34, 12.3],
    [12.36, 12.4],
    [7, 7]
  ])('rounds %s to %s', (value, rounded) => {
    expect(plot.round(value)).toBe(rounded)
  })
})
