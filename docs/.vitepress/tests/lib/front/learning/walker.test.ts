import { describe, expect, it } from 'vitest'

import { fillsOf }     from '../../../../lib/front/learning/tints.ts'
import { Walker }      from '../../../../lib/front/learning/walker.ts'
import { frameFor }    from '../../../../lib/game/actors.ts'
import type { Stance } from '../../../../lib/game/gait.ts'
import * as screen     from '../../../../lib/game/screen.ts'
import { Recorder }    from '../../../common/canvas.ts'

/**
 * The stances of a press Blue walks in, walking through its middle and on the
 * other foot through its last quarter.
 */
const PRESS: readonly Stance[] = ['standing', 'walking', 'walking', 'mirrored']

describe('Walker gliding', () => {
  it('stands at his square facing down under the question bubble until a press places him', () => {
    const walker = new Walker([5, 6])

    expect([walker.x, walker.y, walker.facing, walker.bubble, walker.stance])
      .toStrictEqual([5, 6, 'down', 'question', 'standing'])
  })

  it('glides to the next square over the span given, in the stance his press reaches at each moment', () => {
    const walker = new Walker([5, 6])
    walker.place({ at: [6, 6], facing: 'right', sure: true }, false, 60, PRESS)
    const start = [walker.x, walker.stance]

    const midway  = walker.advance(30)
    const halfway = [walker.x, walker.stance]
    walker.advance(30)

    expect([start, midway, halfway, [walker.x, walker.stance], walker.advance(16)])
      .toStrictEqual([[5, 'standing'], true, [5.5, 'walking'], [6, 'mirrored'], false])
  })

  it.each([
    ['jumps', { arrived: false, span: 0 }],
    ['reaches the north edge', { arrived: true, span: 60 }]
  ])('stands where he %s, whatever stances the press holds', (_, { arrived, span }) => {
    const walker = new Walker([5, 6])

    walker.place({ at: [5, 5], facing: 'up', sure: true }, arrived, span, PRESS)
    walker.advance(30)

    expect(walker.stance).toBe('standing')
  })

  it('takes up a glide from wherever the last one stood', () => {
    const walker = new Walker([5, 6])
    walker.place({ at: [6, 6], facing: 'right', sure: true }, false, 60)
    walker.advance(30)

    walker.place({ at: [6, 5], facing: 'up', sure: true }, false, 60)

    expect([walker.x, walker.y]).toStrictEqual([5.5, 6])
  })
})

describe('Walker placing and painting', () => {
  it.each([
    ['faces the way he pressed with no bubble where the table chooses', true, false, 'left', null],
    ['shows the question bubble where the coin chooses', false, false, 'left', 'question'],
    ['faces down under the shock bubble once he arrives', false, true, 'down', 'shock']
  ] as const)('%s', (_, sure, arrived, facing, bubble) => {
    const walker = new Walker([5, 6])

    walker.place({ at: [4, 6], facing: 'left', sure }, arrived, 0)

    expect([walker.x, walker.facing, walker.bubble]).toStrictEqual([4, facing, bubble])
  })

  it('paints his frame in the fills given and his bubble a square above him', () => {
    const recorder = new Recorder()
    const fills    = fillsOf('fern')
    const walker   = new Walker([5, 6])
    const frame    = screen.runsFor(frameFor('player', 'down').grid)

    walker.paint(recorder, fills, 40, 50)
    const sprite = recorder.marks.slice(0, frame.length).map(mark => mark.y)
    const bubble = recorder.marks.slice(frame.length).map(mark => mark.y)

    expect([Math.min(...sprite), Math.min(...bubble), Math.max(...bubble)])
      .toStrictEqual([50, 50 - screen.SQUARE, 49])
    expect(recorder.marks.map(mark => mark.fill)).toDrawFrom(fills)
  })

  it('paints no bubble where the table chooses his next press', () => {
    const recorder = new Recorder()
    const walker   = new Walker([5, 6])
    walker.place({ at: [5, 6], facing: 'down', sure: true }, false, 0)

    walker.paint(recorder, fillsOf('denim'), 0, 0)

    expect(recorder.marks).toHaveLength(screen.runsFor(frameFor('player', 'down').grid).length)
  })
})
