import { describe, expect, it } from 'vitest'

import { spreadOf } from '../../../../docs/.vitepress/lib/results/aggregate-columns.ts'

describe('spreadOf', () => {
  it.each([
    ['whole where the column holds them', 200, { offsets: [-40, -20, 0, 20, 40], pitch: 20, scale: 1 }],
    ['shrunk where it does not', 50, { offsets: [-20, -10, 0, 10, 20], pitch: 10, scale: 0.5 }]
  ])('lays five marks across a column %s', (_, step, spread) => {
    expect(spreadOf(5, 4, 16, step)).toStrictEqual(spread)
  })
})
