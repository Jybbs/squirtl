import { describe, expect, it } from 'vitest'

import * as experience from '../../../lib/methods/experience.ts'

describe('agesOf', () => {
  it('reads a batch of ages from replay memory, newest first, the same for one update and another for the next', () => {
    const ages = experience.agesOf(3)

    expect([
      ages.length,
      ages.every(age => Number.isInteger(age)),
      Math.min(...ages) >= 0,
      Math.max(...ages) < experience.MEMORY.capacity,
      ages.toSorted((a, b) => a - b),
      experience.agesOf(3),
      experience.agesOf(4).join() === ages.join()
    ]).toStrictEqual([experience.MEMORY.batch, true, true, true, ages, ages, false])
  })
})

describe('figuresOf', () => {
  it('reads the median of the middle two, the newest, and the oldest', () => {
    expect(experience.figuresOf([2, 4, 7, 9])).toStrictEqual({ median: 6, newest: 2, oldest: 9 })
  })
})

describe('the line of time', () => {
  it('sets now at the update and the oldest step replay memory holds at the left end', () => {
    expect([experience.xOf(0), experience.xOf(experience.MEMORY.capacity), experience.TICKS])
      .toStrictEqual([experience.LINE.right, experience.LINE.left, [100_000, 75_000, 50_000, 25_000, 0]])
  })

  it('draws an arc from the update to the lane, rising higher the older the step', () => {
    expect([experience.arcOf(0), experience.arcOf(experience.MEMORY.capacity)])
      .toStrictEqual(['M616 18 Q616 124 616 136', 'M616 18 Q320 34 24 136'])
  })

  it('rests on each update long enough for every arc to move in turn', () => {
    expect(experience.BEAT).toBe((experience.MEMORY.batch + 10) * experience.STEP)
  })
})

describe('the windows', () => {
  it('plays one walk to its end for each environment', () => {
    expect([experience.WALKS.length, experience.WALKS.every(walk => walk.length > 1), experience.WALKS[0]![0]!.place])
      .toStrictEqual([8, true, 'bedroom'])
  })

  it('shows a step of the walk the read draws from, its age wrapping round the walk', () => {
    const walk = experience.WALKS[1]!

    expect([experience.shownOf(walk.length + 2, 9), experience.walkOf(2)[2]]).toStrictEqual([walk[2], walk[2]])
  })

  it('sits under where its arc lands, kept inside the strip and alternating between two rows', () => {
    expect([experience.windowAt(0, 0), experience.windowAt(experience.MEMORY.capacity, 1), experience.windowAt(50_000, 2)])
      .toStrictEqual([{ left: (640 - 48) / 640, top: 0 }, { left: 0, top: 0.5 }, { left: (320 - 24) / 640, top: 0 }])
  })
})
