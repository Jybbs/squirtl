// @vitest-environment happy-dom
import { describe, expect, it } from 'vitest'

import { RoomImages }         from '../../../../lib/game/images.ts'
import { SEGMENTS, TIMING }   from '../../../../lib/methods/curriculum.ts'
import { LaneScreen, laneAt } from '../../../../lib/methods/curriculum/screens.ts'
import { Recorder }           from '../../../common/canvas.ts'

/**
 * A recorder that also takes the outline a lane rings its goal's square with.
 */
class Ringed extends Recorder {
  lineWidth   = 1
  strokeStyle = ''
  readonly rings: number[][] = []

  strokeRect(...args: number[]): void {
    this.rings.push(args)
  }
}

const images = () => new RoomImages(() => new Image())

describe('a lane’s screen', () => {
  it('replays the recording in gray up to the start, then stands the agent there', () => {
    expect([laneAt(100, 0), laneAt(100, TIMING.replay / 2), laneAt(100, TIMING.replay), laneAt(0, 0)]).toStrictEqual([
      { phase: 'recording', step: 0 }, { phase: 'recording', step: 50 }, { phase: 'agent', step: 100 }, { phase: 'agent', step: 0 }
    ])
  })

  it('rings the goal’s square in the goal’s room, and none back in the bedroom', () => {
    const screen  = new LaneScreen(SEGMENTS[2]!, images())
    const context = new Ringed()

    screen.draw(context as never, SEGMENTS[2]!.end)
    const rung = context.rings.length
    screen.draw(context as never, 0)

    expect([rung, context.rings.length, context.lineWidth]).toStrictEqual([1, 1, 2])
  })
})
