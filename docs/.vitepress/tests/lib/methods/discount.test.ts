import { describe, expect, it } from 'vitest'

import * as discount from '../../../lib/methods/discount.ts'

/**
 * The chart laid out at 640 pixels for the discount the settings declare.
 */
const PLOT = discount.plotOf(discount.DISCOUNT, 640)

describe('the discount', () => {
  it('counts half at about 231 steps at the setting, which the slider starts on', () => {
    expect([Math.round(discount.halfLife(discount.DISCOUNT)), discount.discountAt(discount.stopOf(discount.DISCOUNT))])
      .toStrictEqual([231, discount.DISCOUNT])
  })

  it.each([
    [0, 50],
    [discount.WEIGHING.stops, 3000]
  ])('keeps the half life the slider’s stop %i sets at %i steps', (stop, half) => {
    expect(Math.round(discount.halfLife(discount.discountAt(stop)))).toBe(half)
  })

  it('catches each named discount as the half point passes it', () => {
    expect(discount.NAMED.map(named => discount.discountAt(discount.stopOf(named) + 1))).toStrictEqual([...discount.NAMED])
  })

  it.each([
    [0.997, '0.997'],
    [0.9951, '0.9951']
  ])('spells %f as %s', (value, text) => {
    expect(discount.spelled(value)).toBe(text)
  })

  it('weighs the starter at its payment where it arrives at once', () => {
    expect(discount.weightOf(0.5, 0)).toBe(0.6)
  })
})

describe('EPISODES', () => {
  it('walks to the starter in a few hundred steps and wanders to it in thousands', () => {
    expect(discount.EPISODES.map(episode => episode.told)).toStrictEqual([
      'The walk to the starter in 180 steps', 'A wander to the starter in 8,933 steps'
    ])
  })

  it('names an episode that never reaches the starter as such', () => {
    expect(discount.weighed('A wander', 'random', Infinity, 1000).told).toBe('A wander never reaching the starter')
  })
})

describe('plotOf', () => {
  it('labels the weights up the side and each power of ten along the bottom', () => {
    expect(PLOT.labels.map(label => label.text)).toStrictEqual(['0.0', '0.5', '1.0', '1', '10', '100', '1,000', '10,000'])
  })

  it('sets the half point on the curve with its label to its right while room remains', () => {
    expect(PLOT.half).toStrictEqual({
      label : { anchor: 'start', text: 'Half its weight at 231 steps', x: 397.4, y: 168 },
      x     : 383.4,
      y     : 180
    })
  })

  it('sets the half point’s label to its left near the chart’s right edge', () => {
    expect(discount.plotOf(0.9997, 640).half.label.anchor).toBe('end')
  })

  it('marks a stop on the half line at each named discount', () => {
    expect(PLOT.stops).toStrictEqual([308.1, 383.4, 452])
  })

  it('sets a dot on the curve for each payment that jumps either return', () => {
    expect(PLOT.dots.map(dot => [dot.player, dot.term])).toStrictEqual([
      ['agent', 'milestone'], ['agent', 'milestone'], ['agent', 'milestone'], ['agent', 'starter'],
      ['random', 'milestone'], ['random', 'milestone'], ['random', 'milestone'], ['random', 'starter']
    ])
  })

  it('groups the tiles of payments under eight pixels apart under one leader, combed beneath them', () => {
    expect(PLOT.lanes.map(lane => lane.groups.map(group => group.tiles.length))).toStrictEqual([[1, 2, 1], [4]])
    expect(PLOT.lanes[0]!.groups[1]!.leader).toMatch(/^M[\d.]+,33H[\d.]+(M[\d.]+,28V33){2}M[\d.]+,33L/u)
  })

  it('keeps each row of tiles a pitch apart and inside the chart', () => {
    const [walk, wander] = PLOT.lanes.map(lane => lane.groups.flatMap(group => group.tiles.map(tile => tile.x)))

    expect([wander![0]! - walk!.at(-1)! >= discount.WEIGHING.pitch, wander!.at(-1)! <= 640 - discount.WEIGHING.box.right])
      .toStrictEqual([true, true])
  })
})
