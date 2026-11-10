import { describe, expect, it } from 'vitest'

import { LAST }  from '../../../../lib/methods/memory.ts'
import * as says from '../../../../lib/methods/memory/says.ts'

describe('the sentences', () => {
  it('names the position the episode starts on with no payment', () => {
    expect(says.textOf(says.partsOf(says.SAYS[0]!, false))).toBe('Step 0 stands on (26, 03, 06) in the bedroom.')
  })

  it('names each flag set with its bit and byte, and the starter ending the episode', () => {
    expect(says.textOf(says.partsOf(says.SAYS[LAST]!, false))).toBe(
      `Step ${LAST} sets Got the starter (bit 2 of D74B), paying 0.60000, which ends the episode.`
    )
  })

  it('pays nothing for a press that only turns Blue', () => {
    expect(says.textOf(says.partsOf(says.SAYS[1]!, false))).toBe('Step 1 turns Blue to face right on (26, 03, 06) without a step, paying nothing.')
  })

  it('names a square reached before as paying nothing for the position', () => {
    const again = says.SAYS.find(say => say.did.some(([words]) => words === ', reached before'))!

    expect([again.paid, again.term]).toStrictEqual([0, null])
  })

  it('reads a pointed square as reached or not by the step', () => {
    expect([
      says.textOf(says.partsOf(says.pointedSay('bedroom', [3, 6], 0), true)),
      says.pointedSay('pallet', [0, 0], 0).term
    ]).toStrictEqual(['(26, 03, 06) is reached by step 0, so stepping onto it again pays nothing.', 'novelty'])
  })

  it('lays the longest sentence under every one shown', () => {
    expect(says.SAYS.every(say => says.textOf(says.partsOf(say, false)).length <= says.LONGEST.length)).toBe(true)
  })
})
