import { describe, expect, it } from 'vitest'

import type { Moment } from '../../../../lib/front/learning.ts'
import * as strip      from '../../../../lib/front/learning/strip.ts'
import { hexOf }       from '../../../../lib/identity/identity.ts'

/**
 * Makes a pointer event of `pointerType` at `clientY` over a strip whose top
 * sits 100 pixels down the viewport.
 */
function pointing(clientY: number, pointerType: string): PointerEvent {
  const event = { clientY, currentTarget: { getBoundingClientRect: () => ({ top: 100 }) }, pointerType }
  return event as unknown as PointerEvent
}

/**
 * Makes a walk `presses` presses long that reached the north edge.
 */
function walkOf(presses: number): Moment {
  return { episodes: 1, presses, reached: true, steps: [] }
}

describe('stripRows', () => {
  it('sets the pins beneath the last band and the counts beneath the pins', () => {
    const { band, label, overhang, row, tile, top } = strip.STRIP
    const rows                                      = strip.stripRows(4)

    expect(rows.pins).toBeGreaterThan(top + row * 3 + band)
    const labels = rows.pins + tile + label

    expect([rows.labels, rows.height]).toStrictEqual([labels, labels + overhang])
  })
})

describe('stripClockAt', () => {
  const { chip } = strip.STRIP
  const walks    = [walkOf(100), walkOf(200)]

  it.each([
    ['at its first press, its chip held at the left edge', 0, { ended: 0, left: 0, now: 0 }],
    ['where the shorter walk ends', 100, { ended: 1, left: 200 - chip / 2, now: 200 }],
    ['at its last press, its chip held at the right edge', 200, { ended: 3, left: 400 - chip, now: 400 }]
  ])('sets the clock of a strip 400 pixels wide %s', (_, at, clock) => {
    expect(strip.stripClockAt(at, walks, 400)).toStrictEqual(clock)
  })
})

describe('rowAt', () => {
  const { band, row, top } = strip.STRIP

  it.each([
    ['above the first band', top - row, undefined],
    ['just above the first band', top - 1, 0],
    ['on the first band', top + band / 2, 0],
    ['on the third band', top + row * 2 + 1, 2],
    ['on the last band', top + row * 3 + band, 3],
    ['below the last band', top + row * 5, undefined]
  ])('finds the walk %s', (_, y, walk) => {
    expect(strip.rowAt(4, y)).toBe(walk)
  })
})

describe('ticksOf', () => {
  it.each([
    [200, [0, 50, 100, 150, 200]],
    [184, [0, 50, 100, 150]],
    [12, [0]]
  ])('counts the presses of a strip %i presses long every fifty', (longest, ticks) => {
    expect(strip.ticksOf(longest)).toStrictEqual(ticks)
  })
})

describe('hatchMarkup', () => {
  it('draws a stripe half the hatch’s cell wide in each cell, the cells turned through 45 degrees', () => {
    expect(strip.hatchMarkup('#000', 'walk', { ...strip.STRIP, hatch: 6 })).toBe(
      '<pattern id="walk" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">'
      + '<rect width="3" height="6" fill="#000"/></pattern>'
    )
  })
})

describe('keyMark', () => {
  it('draws the table’s band solid in Denim Deep', () => {
    const band = `<rect x="1" y="5.5" width="14" height="5" fill="${hexOf('deep')}"/>`

    expect(strip.keyMark('key-table', true)).toBe(`<svg viewBox="0 0 16 16">${band}</svg>`)
  })

  it('draws the coin’s band in a hatch of its own pattern', () => {
    const mark = strip.keyMark('key-coin', false)

    expect(mark).toContain('<pattern id="key-coin"')
    expect(mark).toContain('fill="url(#key-coin)"')
    expect(mark).toContain(`fill="${hexOf('deep')}"`)
  })
})

describe('walkUnder', () => {
  const { row, top } = strip.STRIP

  it.each([
    ['the walk under a mouse', 100 + top + row + 1, 'mouse', 1],
    ['no walk for a mouse beside every band', 100, 'mouse', null],
    ['no walk for a touch', 100 + top + row + 1, 'touch', null]
  ])('finds %s', (_, clientY, pointerType, walk) => {
    expect(strip.walkUnder(pointing(clientY, pointerType), 4)).toBe(walk)
  })
})
