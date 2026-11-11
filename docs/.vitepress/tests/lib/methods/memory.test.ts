import { describe, expect, it } from 'vitest'

import { Player }  from '../../../lib/game/player.ts'
import * as memory from '../../../lib/methods/memory.ts'

describe('the bytes', () => {
  it('reads each address `Symbol` declares, valued at the symbol file', () => {
    expect(Object.values(memory.ADDRESS).map(at => memory.address(at))).toStrictEqual(['D747', 'D35E', 'D362', 'D361'])
  })

  it('sets each flag at bit `index % 8` of the byte `index // 8` past wEventFlags', () => {
    expect(memory.FLAG_BITS.map(each => [each.flag, memory.address(each.address), each.bit])).toStrictEqual([
      ['appeared', 'D74B', 7], ['followed', 'D747', 0], ['asked', 'D74B', 1], ['starter', 'D74B', 2]
    ])
  })

  it('turns bit 0 of the second byte on beside the first flag, as the lab script sets both', () => {
    const bytes = memory.bytesOf('lab', [5, 3], new Set(['followed', 'asked']))

    expect([bytes.get(memory.ADDRESS.flags), bytes.get(memory.SECOND), bytes.get(memory.ADDRESS.map)]).toStrictEqual([1, 0b11, 0x28])
  })

  it('writes a byte in two capital digits', () => {
    expect([memory.byte(10), memory.byte(0x28)]).toStrictEqual(['0A', '28'])
  })
})

describe('the trace', () => {
  it('plays from the bedroom to the starter, a row a step after the reset', () => {
    const first = memory.TRACE[0]!
    const last  = memory.TRACE[memory.LAST]!

    expect([first.place, first.at, last.flags.has('starter'), memory.TRACE.length]).toStrictEqual(['bedroom', [3, 6], true, memory.LAST + 1])
  })

  it('reads the same trace from a player of the same seed', () => {
    expect(memory.traceOf(new Player()).map(row => row.at)).toStrictEqual(memory.TRACE.map(row => row.at))
  })

  it('reaches each square first on the step the newest names it', () => {
    expect(memory.NEWEST.every((row, n) => memory.FIRST.get(`${row.place}:${row.at[0]},${row.at[1]}`)! <= n)).toBe(true)
  })
})

describe('the steps', () => {
  it('describes a step for a screen reader', () => {
    expect(memory.describe(3)).toBe(`Step 3 of ${memory.LAST}`)
  })
})
