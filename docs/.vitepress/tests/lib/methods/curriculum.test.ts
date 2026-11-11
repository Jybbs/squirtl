import { describe, expect, it } from 'vitest'

import * as curriculum from '../../../lib/methods/curriculum.ts'
import { TRACE }       from '../../../lib/methods/memory.ts'
import SETTINGS        from '../../../lib/rendered/settings.json' with { type: 'json' }

describe('the segments', () => {
  it('ends a segment at each press first setting a flag the reward pays, Oak’s speech falling between following him in and his asking', () => {
    expect(curriculum.SEGMENTS.map(each => [each.term, each.tag])).toStrictEqual([
      ['milestone', 'Oak stops Blue'], ['milestone', 'Blue follows Oak in'], ['milestone', 'Oak asks Blue to choose'],
      ['starter', 'Blue takes a starter']
    ])
    expect(curriculum.SEGMENTS.every(({ end }) => [...TRACE[end + 1]!.flags].some(flag => !TRACE[end]!.flags.has(flag)))).toBe(true)
  })

  it('reads the curriculum the settings declare', () => {
    expect(curriculum.CURRICULUM.window).toBe(SETTINGS.curriculum.window)
  })
})

describe('the run', () => {
  it('keeps every start between the bedroom and its segment’s end, a segment staying solved once solved', () => {
    const ends   = curriculum.SEGMENTS.map(each => each.end)
    const solved = curriculum.RUN.map(batch => batch.filter(each => each.solved).length)

    expect(Math.min(...curriculum.RUN.flat().map(each => each.start))).toBe(0)
    expect(curriculum.RUN.flat().filter((shown, n) => shown.start > ends[n % ends.length]!)).toStrictEqual([])
    expect(solved).toStrictEqual(solved.toSorted((left, right) => left - right))
  })

  it('opens on the window at each segment’s end and closes once every segment is solved', () => {
    const first = curriculum.RUN[0]!

    expect(first.every((shown, k) => shown.start >= curriculum.SEGMENTS[k]!.end - curriculum.CURRICULUM.window)).toBe(true)
    expect(curriculum.RUN.at(-1)!.map(each => each.start)).toStrictEqual([0, 0, 0, 0])
  })

  it('moves a window forward where too few episodes succeed, solving the run later', () => {
    const strict = curriculum.runOf({ ...curriculum.CURRICULUM, required: 0.9 })
    const ends   = curriculum.SEGMENTS.map(each => each.end)

    expect(strict.length).toBeGreaterThan(curriculum.BATCHES)
    expect(strict.flat().every((shown, n) => shown.start <= ends[n % ends.length]!)).toBe(true)
  })

  it('reads the odds of reaching a goal as falling with the steps left and rising with training, within their bounds', () => {
    expect([curriculum.odds(1000, 0), curriculum.odds(0, 100), curriculum.odds(8, 0)]).toStrictEqual([0.02, 0.99, 0.5])
  })
})

describe('the words', () => {
  it('names a batch and the segments solved by its end', () => {
    expect([curriculum.describe(0), curriculum.describe(curriculum.BATCHES - 1)]).toStrictEqual([
      `Batch 1 of ${curriculum.BATCHES}, 0 of 4 segments solved`, `Batch ${curriculum.BATCHES} of ${curriculum.BATCHES}, 4 of 4 segments solved`
    ])
  })

  it('writes how far before its goal an episode starts, from the bedroom, or the segment solved', () => {
    const last   = curriculum.BATCHES - 1
    const { end } = curriculum.SEGMENTS[0]!
    const start  = curriculum.RUN[0]![0]!.start

    expect([curriculum.farOf(0, 0), curriculum.farOf(last, 0), curriculum.farOf(last, curriculum.SEGMENTS.length - 1)])
      .toStrictEqual([`${end + 1 - start} presses before it`, 'Solved from the bedroom', 'From the bedroom'])
  })

  it('lays the places out in the order Blue reaches them, covering the recording', () => {
    expect(curriculum.STRETCHES.map(each => each.name)).toStrictEqual(['Bedroom', 'House', 'Pallet Town', 'Oak’s Lab'])
    expect([curriculum.STRETCHES[0]!.first, curriculum.STRETCHES.at(-1)!.last]).toStrictEqual([0, curriculum.LAST])
    expect([curriculum.along(0), curriculum.along(curriculum.LAST + 1)]).toStrictEqual([0, 1])
  })
})
