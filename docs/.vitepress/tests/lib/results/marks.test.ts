import { describe, expect, it } from 'vitest'

import { glyphOf, outlineOf } from '../../../lib/results/marks.ts'

describe('glyphOf', () => {
  it.each(['dqn', 'ppo', 'pqn'] as const)('draws %s’s glyph as the game’s pixels, hollow along the curriculum', agent => {
    const [solid, hollow] = [false, true].map(curriculum => glyphOf({ agent, curriculum }))

    expect([solid!.startsWith('<svg viewBox="0 0 8 8" shape-rendering="crispEdges">'), solid === hollow]).toStrictEqual([true, false])
  })
})

describe('outlineOf', () => {
  it('keeps each set pixel bordering a clear one or the edge', () => {
    expect(outlineOf(['0000', '0333', '0333', '0333'])).toStrictEqual(['0000', '0333', '0303', '0333'])
  })
})
