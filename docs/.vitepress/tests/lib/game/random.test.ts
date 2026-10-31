import { describe, expect, it } from 'vitest'

import { pickFrom, seeded } from '../../../lib/game/random.ts'

describe('seeded', () => {
  it.each([
    [1, [0.6270739405881613, 0.002735721180215478, 0.5274470399599522]],
    [11, [0.5115870486479253, 0.5299464082345366]]
  ])('returns the draws the board shows for seed %i', (seed, draws) => {
    const random = seeded(seed)

    expect(draws.map(() => random())).toStrictEqual(draws)
  })

  it('returns one sequence from one seed and draws only from zero up to one', () => {
    const [first, second] = [seeded(2 ** 31 + 5), seeded(2 ** 31 + 5)]
    const draws           = Array.from({ length: 500 }, () => first())

    expect(draws).toStrictEqual(Array.from({ length: 500 }, () => second()))
    expect(Math.min(...draws)).toBeGreaterThanOrEqual(0)
    expect(Math.max(...draws)).toBeLessThan(1)
  })
})

describe('pickFrom', () => {
  it.each([
    [0, 'up'],
    [0.5, 'left'],
    [0.999, 'right']
  ])('picks the item a draw of %f lands on', (draw, item) => {
    expect(pickFrom(['up', 'down', 'left', 'right'], () => draw)).toBe(item)
  })
})
