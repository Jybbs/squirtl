import { describe, expect, it } from 'vitest'

import { IDENTITY, type Hue } from '../../../lib/identity/identity.ts'
import * as order             from '../../../lib/identity/order.ts'

/**
 * Every series hue, in the identity's order.
 */
const HUES = IDENTITY.order as Hue[]

/**
 * The margins a case lays a chart out inside.
 */
const MARGINS = { bottom: 10, left: 20, right: 10, top: 10 }

describe('RUNS', () => {
  it('makes one run for each series hue in the order, each carrying its hue’s role', () => {
    expect(order.RUNS.map(run => [run.hue, run.role, run.place]))
      .toStrictEqual(HUES.map((hue, place) => [hue, Object.entries(IDENTITY.roles).find(([, each]) => each === hue)![0], place]))
  })

  it('keeps every value of every run between 0 and 1 across every step', () => {
    const values = order.RUNS.flatMap(run => run.values)

    expect(order.RUNS.map(run => run.values.length)).toStrictEqual(HUES.map(() => order.STEPS))
    expect(Math.min(...values)).toBeGreaterThanOrEqual(0)
    expect(Math.max(...values)).toBeLessThanOrEqual(1)
  })
})

describe('tagOf', () => {
  it('names a run by its place from 1 and its hue’s color', () => {
    expect(order.tagOf(order.RUNS[0]!)).toBe(`1 · ${IDENTITY.colors.primary.name}`)
  })
})

describe('penOf', () => {
  it.each([[true, 1], [false, 0]])('draws every line whole where whole is %s, as %d', (whole, drawn) => {
    expect(order.penOf(whole)).toStrictEqual({ active: null, drawn: Object.fromEntries(HUES.map(hue => [hue, drawn])), rewinding: false })
  })
})

describe('advance', () => {
  it('draws the first line shown that is not whole, at the pace of one line per draw', () => {
    const pen = order.penOf(false)

    expect(order.advance(pen, new Set(HUES), order.TEMPO.draw / 2)).toBe(true)
    expect([pen.active, pen.drawn[HUES[0]!], pen.drawn[HUES[1]!]]).toStrictEqual([HUES[0], 0.5, 0])
  })

  it('passes over a line hidden to the next shown', () => {
    const pen = order.penOf(false)
    order.advance(pen, new Set(HUES.slice(1)), order.TEMPO.draw)

    expect([pen.active, pen.drawn[HUES[1]!]]).toStrictEqual([HUES[1], 1])
  })

  it('rewinds a line hidden while the pen draws another', () => {
    const pen = order.penOf(true)
    order.advance(pen, new Set(HUES.slice(1)), order.TEMPO.rewind / 4)

    expect([pen.active, pen.drawn[HUES[0]!]]).toStrictEqual([null, 0.75])
  })

  it('rewinds the last line drawn first, then draws from the first once every line is rewound', () => {
    const pen     = order.penOf(true)
    pen.rewinding = true
    order.advance(pen, new Set(HUES), order.TEMPO.rewind)
    const first   = [pen.active, pen.drawn[HUES.at(-1)!]]
    for (const _ of HUES.slice(1)) order.advance(pen, new Set(HUES), order.TEMPO.rewind)
    order.advance(pen, new Set(HUES), order.TEMPO.draw / 4)

    expect([first, pen.rewinding, pen.active, pen.drawn[HUES[0]!]]).toStrictEqual([[HUES.at(-1), 0], false, HUES[0], 0.25])
  })

  it('reports no move once every line shown is whole and every other none', () => {
    const pen = order.penOf(true)

    expect([order.advance(pen, new Set(HUES), 16), pen.active]).toStrictEqual([false, null])
  })
})

describe('finish', () => {
  it('sets every line shown whole and every other none, the pen at rest', () => {
    const pen = { ...order.penOf(false), active: HUES[0]!, rewinding: true }
    order.finish(pen, new Set([HUES[1]!]))

    expect(pen).toStrictEqual({ active: null, drawn: Object.fromEntries(HUES.map(hue => [hue, Number(hue === HUES[1])])), rewinding: false })
  })
})

describe('pointAt', () => {
  it.each([
    [0, [0, 0]],
    [0.25, [5, 0]],
    [0.75, [10, 5]],
    [1, [10, 10]],
    [2, [10, 10]]
  ] as const)('finds the point %d of the way along the line by its length', (share, point) => {
    expect(order.pointAt([[0, 0], [10, 0], [10, 10]], share)).toStrictEqual(point)
  })

  it('passes over a stretch of no length', () => {
    expect(order.pointAt([[0, 0], [0, 0], [4, 0]], 0.5)).toStrictEqual([2, 0])
  })

  it('reads a line folded onto one point as that point', () => {
    expect(order.pointAt([[1, 1], [1, 1]], 0.5)).toStrictEqual([1, 1])
  })

  it('reads a line of one point as that point', () => {
    expect(order.pointAt([[3, 4]], 0.5)).toStrictEqual([3, 4])
  })
})

describe('pointsOf', () => {
  it('lays the run’s first value at the left margin and its last at the right, each value up from the bottom', () => {
    const run    = { ...order.RUNS[0]!, values: [0, ...Array.from({ length: order.STEPS - 2 }, () => 0.5), 1] }
    const points = order.pointsOf(run, 120, 60, MARGINS)

    expect([points[0], points.at(-1)]).toStrictEqual([[20, 50], [110, 10]])
  })
})

describe('pathOf', () => {
  it('moves to the first point and draws a line through each other', () => {
    expect(order.pathOf([[0, 0], [1.24, 2], [3, 4.5]])).toBe('M0.0,0.0L1.2,2.0L3.0,4.5')
  })
})
