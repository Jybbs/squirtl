import { describe, expect, it } from 'vitest'

import { LAST, along } from '../../../../lib/methods/curriculum.ts'
import { placeOf }     from '../../../../lib/methods/curriculum/lanes.ts'

const SIZES = { far: 100, gap: 8, screen: 80, track: 600 }

describe('a lane', () => {
  it('centers the screen on the start, gray up to it and Denim on to the goal', () => {
    const placed = placeOf(SIZES, 82, 122, 'right')
    const at     = along(82) * 600

    expect(placed).toStrictEqual({ at, far: at - 40 + 80 + 8, reach: along(123) * 600 - at, screen: at - 40, side: 'right' })
  })

  it('holds the screen inside the track at either end', () => {
    expect([placeOf(SIZES, 0, 10, 'right').screen, placeOf(SIZES, LAST, LAST, 'left').screen]).toStrictEqual([0, 520])
  })

  it('keeps the figure on its side while it fits there, and moves it only once the screen leaves it no room', () => {
    expect([
      placeOf(SIZES, 82, 122, 'left').side,
      placeOf(SIZES, 160, 162, 'right').side,
      placeOf(SIZES, 5, 130, 'left').side
    ]).toStrictEqual(['left', 'left', 'right'])
  })

  it('stands the figure a spacing from the screen where no gap is given', () => {
    const { far, screen } = placeOf({ far: 10, screen: 80, track: 600 }, 0, 10, 'right')

    expect(far - screen - 80).toBeGreaterThan(0)
  })
})
