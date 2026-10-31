import { describe, expect, it } from 'vitest'

import * as transition from '../../../../lib/front/learning/transition.ts'
import { FRAME }       from '../../../../lib/game/screen.ts'
import { hexOf }       from '../../../../lib/identity/identity.ts'
import { Recorder }    from '../../../common/canvas.ts'

/**
 * The transition's timing, read once for every case.
 */
const PHASES = transition.phasesOf()

/**
 * Four pixels of the town in the order a case reads them back: white, the
 * darkest shade, the palest blue, and the middle one.
 */
const PIXELS = Uint8ClampedArray.from([
  243, 244, 247, 255, 41, 78, 149, 255, 146, 177, 232, 255, 112, 151, 223, 255
])

/**
 * Reads the colors of `pixels` back as hexes, one to a pixel.
 */
const hexesOf = (pixels: Uint8ClampedArray): string[] => Array.from({ length: pixels.length / 4 }, (_, n) => {
  const [red, green, blue] = pixels.subarray(n * 4, n * 4 + 3)
  return `#${[red, green, blue].map(byte => byte!.toString(16).padStart(2, '0')).join('')}`
})

describe('phasesOf', () => {
  it('times the flash, the circle, the black, and the fade in the Game Boy’s own frames', () => {
    expect([PHASES.flash, PHASES.circle, PHASES.black, PHASES.end].map(ms => Math.round(ms / FRAME)))
      .toStrictEqual([72, 102, 112, 144])
  })
})

describe('paletteAt', () => {
  it.each([
    ['opens the flash on its first palette', 0, '3321'],
    ['steps the flash every two frames', PHASES.flashStep + 1, '3332'],
    ['flashes to white midway through a run', PHASES.flashStep * 8 + 1, '0000'],
    ['runs the flash a second time', PHASES.flashStep * 12 + 1, '3321'],
    ['keeps the town’s own palette while the circle closes', PHASES.flash + 1, '3210'],
    ['holds black once the circle has closed', PHASES.circle, '3333'],
    ['fades in from black', PHASES.black + PHASES.fadeStep + 1, '3332'],
    ['ends the fade on the town’s own palette', PHASES.end + 100, '3210']
  ])('%s', (_, t, palette) => {
    expect(transition.paletteAt(t)).toBe(palette)
  })
})

describe('spritesAt and tileStepAt', () => {
  it.each([
    ['before the circle', PHASES.flash - 1, true, -1],
    ['as the circle opens', PHASES.flash, true, 0],
    ['at the circle’s last step', PHASES.circle - 1, true, 9],
    ['while the screen holds black', PHASES.circle + 1, false, -1],
    ['on the fade’s first palette', PHASES.black + 1, false, -1],
    ['once the fade lifts black', PHASES.black + PHASES.fadeStep + 1, true, -1]
  ])('shows the sprites and the circle’s step %s', (_, t, shown, step) => {
    expect([transition.spritesAt(t), transition.tileStepAt(t)]).toStrictEqual([shown, step])
  })
})

describe('circleTilesOf', () => {
  it('blacks every tile in one of the circle’s steps, the halves sweeping from opposite edges', () => {
    const tiles = transition.circleTilesOf()
    const steps = new Map(tiles.map(tile => [`${tile.column},${tile.row}`, tile.step]))
    const at    = (column: number, row: number) => steps.get(`${column},${row}`)!

    expect(tiles).toHaveLength(40 * 19)
    expect(new Set(tiles.map(tile => tile.step))).toStrictEqual(new Set([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]))
    expect([at(0, 0) < at(39, 0), at(39, 18) < at(0, 18)]).toStrictEqual([true, true])
  })
})

describe('paintCircle', () => {
  it.each([0, 4, 9])('fills in the ink every tile the circle has blacked by its step %i', step => {
    const recorder = new Recorder()

    transition.paintCircle(recorder, step, { ink: '#294e95', tiles: transition.circleTilesOf() })

    expect(recorder.marks).toHaveLength(transition.circleTilesOf().filter(tile => tile.step <= step).length)
    const fills = new Set(recorder.marks.map(mark => `${mark.fill} ${mark.width}`))

    expect(fills).toStrictEqual(new Set(['#294e95 8']))
  })
})

describe('townFrom', () => {
  it('reads the view from the town’s image once and keeps it in every palette the transition shows', () => {
    const image  = {} as CanvasImageSource
    const view   = { ...transition.VIEW, height: 1, width: 4 }
    const reader = Object.assign(new Recorder(), { getImageData: () => ({ data: PIXELS }) as ImageData })

    const town = transition.townFrom(reader as unknown as transition.Reader, image, view)

    expect(reader.images).toStrictEqual([[image, 96, 92, 4, 1, 0, 0, 4, 1]])
    expect(town.ink).toBe(hexOf('deep'))
    expect([...town.palettes.keys()].toSorted())
      .toStrictEqual(['0000', '1000', '2100', '3210', '3321', '3332', '3333'])
    expect(hexesOf(town.palettes.get('3333')!.data))
      .toStrictEqual(Array.from<string>({ length: 4 }).fill(hexOf('deep')))
  })

  it('lays the double circle’s tiles over the view it reads', () => {
    const view   = { ...transition.VIEW, height: 8, width: 16 }
    const reader = Object.assign(new Recorder(), { getImageData: () => ({ data: PIXELS }) as ImageData })

    const town = transition.townFrom(reader as unknown as transition.Reader, {} as CanvasImageSource, view)

    expect(town.tiles).toHaveLength(2)
    expect(town.tiles).toStrictEqual(transition.circleTilesOf(transition.TRANSITION.circleSteps, view))
  })
})
