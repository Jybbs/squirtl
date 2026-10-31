import { describe, expect, it } from 'vitest'

import WORLD                             from '../../../lib/art/world.json' with { type: 'json' }
import { runsOf }                        from '../../../lib/drawing/sprites.ts'
import { type Pose, frameFor }           from '../../../lib/game/actors.ts'
import { RoomImages }                    from '../../../lib/game/images.ts'
import type { Direction, Place, Square } from '../../../lib/game/rooms.ts'
import * as screen                       from '../../../lib/game/screen.ts'
import { IDENTITY, hexOf }               from '../../../lib/identity/identity.ts'
import { Recorder }                      from '../../common/canvas.ts'
import { stand }                         from '../../common/episode.ts'

/**
 * A Poké Ball's one frame.
 */
const BALL = IDENTITY.sprites.ball.frames[0]!

/**
 * A Poké Ball's one frame, as drawn unmirrored.
 */
const BALL_POSE: Pose = { grid: BALL, mirrored: false }

/**
 * The fill of the screen's ground and of its fade.
 */
const DEEP = hexOf('deep')

/**
 * The rectangle the whole screen fills.
 */
const WHOLE = { height: 144, width: 160, x: 0, y: 0 }

/**
 * Reads the rectangles `paintSprite` fills for one pose placed and filled as
 * given.
 */
function painted(pose: Pose, x: number, y: number, fills?: readonly string[]) {
  const recorder = new Recorder()
  screen.paintSprite(recorder, pose, x, y, fills)
  return recorder.marks
}

/**
 * Starts an episode with Blue standing on `at` in `place`, stopped facing
 * `facing` where it is given, beside a screen showing it, whose images stand in
 * for each room's own by recording the source each loads.
 */
function shown(place: Place = 'bedroom', at: Square = [3, 6], facing?: Direction) {
  const game  = stand(at, place, facing)
  const view  = new screen.GameScreen(game, new RoomImages(source => ({ source }) as never))
  const drawn = () => {
    const recorder = new Recorder()
    view.draw(recorder)
    return recorder
  }
  return { drawn, game, view }
}

describe('SCREEN and SQUARE', () => {
  it('shows ten squares across and nine down, the Game Boy’s 160 by 144 pixels', () => {
    expect([screen.SCREEN.width / screen.SQUARE, screen.SCREEN.height / screen.SQUARE]).toStrictEqual([10, 9])
  })
})

describe('runsFor', () => {
  it('reads the runs split once for a frame the identity declares, as drawn and mirrored', () => {
    expect([screen.runsFor(BALL), screen.runsFor(BALL, true)])
      .toStrictEqual([runsOf(BALL), runsOf(BALL, true)])
    expect(screen.runsFor(BALL)).toBe(screen.runsFor(BALL))
  })

  it('splits any other frame as it is asked for', () => {
    const ring = ['0110', '1001', '1001', '0110']

    expect(screen.runsFor(ring)).toStrictEqual(runsOf(ring))
  })
})

describe('paintSprite', () => {
  it('fills each run of a frame as one rectangle in its Game Boy shade', () => {
    const fills = [hexOf('ground'), hexOf('pale'), hexOf('deep'), hexOf('night')]
    const marks = runsOf(BALL).map(run => ({
      alpha  : 1,
      fill   : fills[run.shade],
      height : 1,
      width  : run.width,
      x      : 10 + run.x,
      y      : 20 + run.y
    }))

    expect(painted(BALL_POSE, 10, 20)).toStrictEqual(marks)
  })

  it('snaps each rectangle to whole pixels and takes the fills given', () => {
    expect(painted({ grid: ['1'], mirrored: false }, 0.4, 0.6, ['w', 'x']))
      .toStrictEqual([{ alpha: 1, fill: 'x', height: 1, width: 1, x: 0, y: 1 }])
  })
})

describe('GameScreen.draw', () => {
  it('fills the ground, draws the room around Blue, and stands Blue on the screen’s square 4, 4', () => {
    const { drawn } = shown()
    const recorder  = drawn()
    const blue      = frameFor('player', 'down')

    expect(recorder.marks[0]).toStrictEqual({ ...WHOLE, alpha: 1, fill: DEEP })
    expect(recorder.images)
      .toStrictEqual([[{ source: WORLD.bedroom.image.light }, 80, 128, 160, 144, 0, 0, 160, 144]])
    expect(recorder.marks.slice(1)).toStrictEqual(painted(blue, 64, 60))
    expect(recorder.imageSmoothingEnabled).toBe(false)
  })

  it('draws the people in the room before Blue, each four pixels above its square', () => {
    const { drawn } = shown('house', [3, 3])
    const mom       = frameFor('mom', 'left')
    const marks     = painted(mom, 96, 76)

    expect(drawn().marks.slice(1, 1 + marks.length)).toStrictEqual(marks)
  })

  it('draws a Poké Ball four pixels above its square, as every sprite stands', () => {
    const { drawn } = shown('lab', [7, 4])

    expect(drawn().marks).toStrictEqual(expect.arrayContaining(painted(BALL_POSE, 48, 44)))
  })
})

describe('GameScreen.follow', () => {
  it('glides a step to the next square, Blue walking through its middle, and settles there', () => {
    const { game, view } = shown('bedroom', [3, 6], 'left')
    game.press('left')
    view.follow(100)
    const states = [20, 30, 50].map(dt => [view.advance(dt), view.view.at[0], view.stance])

    expect(states).toStrictEqual([[true, 2.8, 'standing'], [true, 2.5, 'walking'], [false, 2, 'standing']])
  })

  it('walks Blue on the other foot through the step after one, his gait’s counters carrying across', () => {
    const { game, view } = shown('pallet', [10, 7], 'up')
    const halfway        = () => {
      game.press('up')
      view.follow(100)
      view.advance(50)
      const { stance }         = view
      const { grid, mirrored } = frameFor('player', 'up', stance)
      view.advance(50)
      return [stance, grid, mirrored]
    }
    const walking = frameFor('player', 'up', 'walking').grid

    expect([halfway(), halfway()]).toStrictEqual([['walking', walking, false], ['mirrored', walking, true]])
  })

  it('runs Blue’s gait through a press that leaves him on his square, and stands him once it ends', () => {
    const { game, view } = shown('bedroom', [3, 6], 'left')
    game.press('up')
    view.follow(100)
    view.advance(100)

    expect([game.turned, view.view.at, view.stance]).toStrictEqual([true, [3, 6], 'standing'])
  })
})

describe('GameScreen.follow without a glide', () => {
  it('sets a step at once where its glide spans no time', () => {
    const { game, view } = shown('bedroom', [3, 6], 'left')
    game.press('left')
    view.follow(0)

    expect([view.advance(16), view.view.at, view.stance]).toStrictEqual([false, [2, 6], 'standing'])
  })

  it('jumps the view a move of more than one square, Blue standing still', () => {
    const { game, view } = shown('bedroom', [3, 6], 'left')
    game.press('left')
    game.press('left')
    view.follow(100)
    view.advance(10)

    expect([view.view.at, view.stance]).toStrictEqual([[1, 6], 'standing'])
  })
})

describe('GameScreen.advance and snap', () => {
  it('fades a change of room in from the ground over the glide’s fade', () => {
    const { drawn, game, view } = shown('bedroom', [7, 2], 'up')
    game.press('up')
    view.follow(100)
    const placed = [view.view.place, view.view.at, view.veil]
    const fading = view.advance(screen.GLIDE.fade / 2)
    const last   = drawn().marks.at(-1)

    expect([placed, fading, last])
      .toStrictEqual([['house', [7, 1], 1], true, { ...WHOLE, alpha: 0.5, fill: DEEP }])
    expect([view.advance(screen.GLIDE.fade / 2), view.veil]).toStrictEqual([false, 0])
  })

  it('glides Oak beside Blue as Oak leads him, and stands Oak on his square once the glide ends', () => {
    const { drawn, game, view } = shown('pallet', [10, 2], 'up')
    game.press('up')
    view.follow(0)
    view.advance(16)
    game.press('b')
    game.press('b')
    view.follow(100)
    view.advance(50)
    const halfway = [...view.leaderAt!]
    const oak     = frameFor('oak', 'down', 'walking')
    const marks   = painted(oak, 64, 76)

    expect([halfway, drawn().marks]).toStrictEqual([[10, 2.5], expect.arrayContaining(marks)])
    expect([view.advance(50), view.leaderAt]).toStrictEqual([false, game.leader!.at])
  })

  it('sets the view on Blue at once when snapped', () => {
    const { game, view } = shown('bedroom', [3, 6], 'left')
    game.press('left')
    view.follow(100)
    view.snap()

    expect([view.view.at, view.stance, view.veil, view.advance(16)])
      .toStrictEqual([[2, 6], 'standing', 0, false])
  })
})
