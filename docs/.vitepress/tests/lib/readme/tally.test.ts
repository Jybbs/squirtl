import { describe, expect, it } from 'vitest'

import { WALKING, walksOf } from '../../../lib/front/learning.ts'
import { Walks }            from '../../../lib/front/learning/walks.ts'
import { PREVIEW }          from '../../../lib/readme/movie.ts'
import { tallyOf }          from '../../../lib/readme/tally.ts'

/**
 * Reads the words of every line `svg` sets, in the order it sets them.
 */
const wordsOf = (svg: string): string[] => [...svg.matchAll(/<text [^>]*>([^<]*)<\/text>/gu)].map(([, text]) => text!)

describe('tallyOf', () => {
  it.each([
    [0, ['50 EPISODES', '0', 'presses']],
    [1, ['50 EPISODES', '1', 'press']],
    [400, ['50 EPISODES', '18', 'presses']]
  ] as const)('counts the presses a walk has made by press %i, stopping at its own', (at, words) => {
    const walks = new Walks(walksOf({ ...WALKING, moments: [50] }))

    expect(wordsOf(tallyOf(at, 304, 'light', PREVIEW.tally, walks))).toStrictEqual(words)
  })
})
