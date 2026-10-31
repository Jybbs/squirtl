import { describe, expect, it } from 'vitest'

import { frameFor }                      from '../../../lib/game/actors.ts'
import { FRAME, paintSprite }            from '../../../lib/game/screen.ts'
import { paintBox, paintText }           from '../../../lib/game/text.ts'
import { rgbOf, spriteShades }           from '../../../lib/identity/identity.ts'
import type { Origin }                   from '../../../lib/missing/city.ts'
import { type CityReader, GlitchScreen } from '../../../lib/missing/screen.ts'
import * as warp                         from '../../../lib/missing/warp.ts'
import { Recorder }                      from '../../common/canvas.ts'

/**
 * A warp of three frames: Blue facing left on his square, Blue off the screen's
 * top, and the screen faded halfway to white.
 */
const FRAMES: warp.WarpFrame[] = [
  { facing: 'left', palette: '3210', y: warp.Y.stand },
  { facing: 'left', palette: '3210', y: warp.Y.gone },
  { facing: 'left', palette: '2100', y: warp.Y.stand }
]

/**
 * A recorder reading every view back with its first pixels in the Game Boy's
 * shades from the lightest to the darkest, as a city cut from Pallet Town's
 * image holds them.
 */
class ShadedRecorder extends Recorder {
  override getImageData(left: number, top: number, width: number, height: number): ImageData {
    const view = super.getImageData(left, top, width, height)
    for (const [at, hex] of spriteShades.entries()) view.data.set([...rgbOf(hex), 255], at * 4)
    return view
  }
}

/**
 * Makes a screen playing `FRAMES` with its city read from an image in the four
 * shades.
 */
function readScreen(): { reader: Recorder, screen: GlitchScreen } {
  const reader = new ShadedRecorder()
  const screen = new GlitchScreen(FRAMES)
  const blocks: Origin[] = [[96, 96], [128, 96]]
  screen.read(reader as unknown as CityReader, {} as CanvasImageSource, blocks, 'squirtl.fyi/missing/')
  return { reader, screen }
}

/**
 * Reads the rectangles Blue's sprite fills facing `facing` from his place on
 * the screen's middle at the height `y`.
 */
function blueAt(facing: warp.WarpFrame['facing'], y: number): Recorder['marks'] {
  const recorder = new Recorder()
  paintSprite(recorder, frameFor('player', facing), 64, y)
  return recorder.marks
}

describe('GlitchScreen.read', () => {
  it('lays the city’s blocks across the screen and sets the AREA UNKNOWN box over its foot', () => {
    const { reader } = readScreen()
    const unknown    = new Recorder()
    paintBox(unknown, { column: 1, columns: 17, row: 13, rows: 4 }, spriteShades)
    paintText(unknown, ' AREA UNKNOWN', 16, 120, spriteShades)

    expect([reader.images.map(image => image.slice(-4)), reader.marks]).toStrictEqual([
      Array.from({ length: 25 }, (_, at) => [(at % 5) * 32, Math.floor(at / 5) * 32, 32, 32]),
      unknown.marks
    ])
  })
})

describe('GlitchScreen.draw', () => {
  it('draws nothing and plays nothing until its city is read', () => {
    const screen  = new GlitchScreen(FRAMES)
    const painter = new Recorder()
    screen.draw(painter)

    expect([screen.advance(FRAME), painter.views, painter.marks]).toStrictEqual([false, [], []])
  })

  it('puts the city in the frame’s palette and draws Blue at the frame’s facing and height', () => {
    const { screen } = readScreen()
    const painter    = new Recorder()
    screen.draw(painter)

    expect([painter.views, painter.marks])
      .toStrictEqual([[expect.any(Object)], blueAt('left', warp.Y.stand)])
  })

  it.each([
    ['off the screen’s top', 1],
    ['while the screen fades', 2]
  ])('leaves Blue out %s', (_, frame) => {
    const { screen } = readScreen()
    const painter    = new Recorder()
    screen.advance(frame * FRAME)
    screen.draw(painter)

    expect([painter.views.length, painter.marks]).toStrictEqual([1, []])
  })
})

describe('GlitchScreen.advance and reset', () => {
  it('moves through the warp a frame of the Game Boy’s at a time and loops back to its start', () => {
    const { screen } = readScreen()
    const frames     = [0, FRAME, FRAME, FRAME].map(elapsed => {
      screen.advance(elapsed)
      return screen.frame
    })

    expect([screen.advance(0), frames]).toStrictEqual([true, [FRAMES[0], FRAMES[1], FRAMES[2], FRAMES[0]]])
  })

  it('sets the warp back to its first frame', () => {
    const { screen } = readScreen()
    screen.advance(2 * FRAME)
    screen.reset()

    expect(screen.frame).toBe(FRAMES[0])
  })

  it('plays the loop the page at a missing address shows unless given another warp', () => {
    expect(new GlitchScreen().frame).toBe(warp.warpLoop[0])
  })
})
