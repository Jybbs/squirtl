import { describe, expect, it } from 'vitest'

import { fillsOf }  from '../../../../lib/front/learning/tints.ts'
import { Walker }   from '../../../../lib/front/learning/walker.ts'
import { frameFor } from '../../../../lib/game/actors.ts'
import * as screen  from '../../../../lib/game/screen.ts'
import { Recorder } from '../../../common/canvas.ts'

describe('Walker gliding', () => {
  it('stands at his square facing down under the question bubble until a press places him', () => {
    const walker = new Walker([5, 6], screen.STRIDE)

    expect([walker.x, walker.y, walker.facing, walker.bubble, walker.stepping])
      .toStrictEqual([5, 6, 'down', 'question', false])
  })

  it('glides to the next square over the span given, in his walking frame mid-glide', () => {
    const walker = new Walker([5, 6], screen.STRIDE)
    walker.place({ at: [6, 6], facing: 'right', sure: true }, false, 60)
    const start = [walker.x, walker.stepping]

    const midway  = walker.advance(30)
    const halfway = [walker.x, walker.stepping]
    walker.advance(30)

    expect([start, midway, halfway, [walker.x, walker.stepping], walker.advance(16)])
      .toStrictEqual([[5, false], true, [5.5, true], [6, false], false])
  })

  it('takes up a glide from wherever the last one stood', () => {
    const walker = new Walker([5, 6], screen.STRIDE)
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
    const walker = new Walker([5, 6], screen.STRIDE)

    walker.place({ at: [4, 6], facing: 'left', sure }, arrived, 0)

    expect([walker.x, walker.facing, walker.bubble]).toStrictEqual([4, facing, bubble])
  })

  it('paints his frame in the fills given and his bubble a square above him', () => {
    const recorder = new Recorder()
    const fills    = fillsOf('fern')
    const walker   = new Walker([5, 6], screen.STRIDE)
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
    const walker   = new Walker([5, 6], screen.STRIDE)
    walker.place({ at: [5, 6], facing: 'down', sure: true }, false, 0)

    walker.paint(recorder, fillsOf('denim'), 0, 0)

    expect(recorder.marks).toHaveLength(screen.runsFor(frameFor('player', 'down').grid).length)
  })
})
