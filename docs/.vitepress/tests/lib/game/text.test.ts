import { describe, expect, it } from 'vitest'

import * as text    from '../../../lib/game/text.ts'
import { Recorder } from '../../common/canvas.ts'

/**
 * The fills a case draws in, the paper first and the ink last.
 */
const SHADES = ['paper', 'light', 'dark', 'ink']

/**
 * Reads the rectangles `marks` fills in ink, each as its left, its top, and its
 * width.
 */
const inked = (marks: Recorder['marks']): number[][] =>
  marks.filter(mark => mark.fill === 'ink').map(({ width, x, y }) => [x, y, width])

describe('paintText', () => {
  it('draws a letter’s pixels in ink from the top left given, as pret/pokered’s font sets the A', () => {
    const recorder = new Recorder()

    text.paintText(recorder, 'A', 16, 120, SHADES)

    expect(inked(recorder.marks).slice(0, 5))
      .toStrictEqual([[19, 120, 1], [18, 121, 1], [20, 121, 1], [18, 122, 1], [20, 122, 1]])
  })

  it('sets each character a tile to the right of the one before, a space drawing nothing', () => {
    const lone   = new Recorder()
    const spaced = new Recorder()

    text.paintText(lone, 'A', 0, 0, SHADES)
    text.paintText(spaced, ' A', 0, 0, SHADES)

    expect(inked(spaced.marks))
      .toStrictEqual(inked(lone.marks).map(([x, y, width]) => [x! + text.TILE, y, width]))
  })
})

describe('paintBox', () => {
  it('fills the box in paper and frames it in the border’s tiles, a corner at each corner', () => {
    const recorder = new Recorder()

    text.paintBox(recorder, { column: 1, columns: 4, row: 2, rows: 3 }, SHADES)

    expect(recorder.marks[0]).toMatchObject({ fill: 'paper', height: 24, width: 32, x: 8, y: 16 })
    expect(inked(recorder.marks)).toStrictEqual(expect.arrayContaining([
      [11, 17, 2], [16, 18, 8], [24, 18, 8], [16, 34, 8], [10, 24, 1], [12, 24, 1], [34, 24, 1], [36, 24, 1]
    ]))
  })
})
