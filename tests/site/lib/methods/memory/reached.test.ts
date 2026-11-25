import { describe, expect, it } from 'vitest'

import { TRACE }   from '../../../../../docs/.vitepress/lib/methods/memory.ts'
import { PLAY }    from '../../../../../docs/.vitepress/lib/methods/memory/play.ts'
import { REACHED } from '../../../../../docs/.vitepress/lib/methods/memory/reached.ts'

describe('REACHED', () => {
  it('shows each square first on a frame of the step that first reaches it', () => {
    const lab = REACHED.lab.at(-1)!

    expect(PLAY.steps[lab.step]!.some(frame => frame.clock === lab.seen)).toBe(true)
  })

  it('lists every square the trace reaches once', () => {
    expect(Object.values(REACHED).flat().length)
      .toBe(new Set(TRACE.map(row => `${row.place}:${row.at.join()}`)).size)
  })
})
