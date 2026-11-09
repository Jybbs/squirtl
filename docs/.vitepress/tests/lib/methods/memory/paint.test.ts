import { describe, expect, it } from 'vitest'

import { hexOf }                  from '../../../../lib/identity/identity.ts'
import { LAST }                   from '../../../../lib/methods/memory.ts'
import * as marks                 from '../../../../lib/methods/memory/marks.ts'
import { paintMap, strengthOf }   from '../../../../lib/methods/memory/paint.ts'
import { FADE, type Frame, PLAY } from '../../../../lib/methods/memory/play.ts'
import { Recorder }               from '../../../common/canvas.ts'

/**
 * The room's render in each palette of the fade, each a plain object standing
 * in for its canvas.
 */
const ROOM = FADE.map(() => ({}) as CanvasImageSource)

/**
 * Draws `frame` onto a recorder from the renders `faded`, and returns the
 * recorder.
 */
function painted(frame: Frame, lit: number | null, faded?: readonly CanvasImageSource[]): Recorder {
  const recorder = new Recorder()
  paintMap(recorder as unknown as CanvasRenderingContext2D, faded, frame, lit)
  return recorder
}

describe('strengthOf', () => {
  it('shows every square in full with no entry picked out, and the newest in full while its entry is', () => {
    expect([strengthOf(null, false), strengthOf(1, true)]).toStrictEqual([1, 1])
  })

  it('strengthens every square while the squares reached are picked out, and fades them under any other entry', () => {
    expect([strengthOf(0, false), strengthOf(1, false), strengthOf(3, true)]).toStrictEqual([1.5, 0.4, 0.4])
  })
})

describe('marks.dotOf', () => {
  it('pops a square in large and settles it small, the newest keeping the middle size', () => {
    expect([marks.dotOf(0, false), marks.dotOf(0.5, false), marks.dotOf(1, true), marks.dotOf(1, false)]).toStrictEqual([
      marks.SHAPES.dot10, marks.SHAPES.dot8, marks.SHAPES.dot8, marks.SHAPES.dot6
    ])
  })
})

describe('paintMap', () => {
  it('fills the room with the ground until its image loads', () => {
    const { cols, rows } = marks.fitOf('bedroom')

    expect(painted(PLAY.ends[0]!, null).marks).toStrictEqual([{ alpha: 1, fill: hexOf('ground'), height: rows * 16, width: cols * 16, x: 0, y: 0 }])
  })

  it('draws the room in the frame’s palette, the squares reached, and the people standing in it', () => {
    const recorder = painted(PLAY.ends[LAST]!, null, ROOM)

    expect([recorder.images, recorder.marks.some(mark => mark.alpha === 1)]).toStrictEqual([[[ROOM[0], 0, 0]], true])
  })

  it('draws nobody over a room faded to black', () => {
    const black = PLAY.steps[0]!.find(frame => frame.fade === FADE.length - 1)!

    expect(painted(black, null, ROOM).marks.every(mark => mark.alpha === 0)).toBe(true)
  })

  it('sets the newest square’s ring back while a later entry of the key is picked out', () => {
    expect([4, null].map(lit => painted(PLAY.ends[LAST]!, lit, ROOM).marks.some(mark => mark.alpha === 0.4))).toStrictEqual([true, false])
  })
})
