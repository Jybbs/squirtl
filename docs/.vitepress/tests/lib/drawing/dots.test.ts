import { describe, expect, it } from 'vitest'

import * as dots    from '../../../lib/drawing/dots.ts'
import { IDENTITY } from '../../../lib/identity/identity.ts'

describe('cellsOf', () => {
  it('reads each cell as its column and its row lowered by five', () => {
    expect(dots.cellsOf('L')).toStrictEqual([
      [0, 0], [0, 1], [0, 2], [0, 3], [0, 4], [0, 5], [1, 0], [1, 1], [1, 2], [1, 3], [1, 4], [1, 5],
      [2, 0], [3, 0]
    ])
  })

  it('draws a character the face declares no glyph for as its question mark', () => {
    expect([dots.cellsOf('☃'), dots.advanceOf('☃')])
      .toStrictEqual([dots.cellsOf('?'), IDENTITY.glyphs['?'].advance])
  })
})

describe('layout', () => {
  it('starts each character where the one before it advances to', () => {
    const { letters, width } = dots.layout('RL')

    expect([letters.map(letter => letter.x), width])
      .toStrictEqual([[0, dots.advanceOf('R')], dots.advanceOf('R') + dots.advanceOf('L') - 1])
  })
})

describe('dotText', () => {
  it('draws one circle per lit cell, each centered in its cell from the baseline', () => {
    const circles = dots.dotText('L', { cell: 10, fill: '#3d6fd0', x: 0, y: 100 })
      .match(/<circle [^>]*\/>/gu)!

    expect(circles).toHaveLength(dots.cellsOf('L').length)
    expect(circles[0]).toBe('<circle cx="5.0" cy="95.0" r="6.0" fill="#3d6fd0"/>')
  })

  it('fills each dot from its column, its row, and its letter where a function sets the fill', () => {
    const drawn = dots.dotText('Lt', {
      cell : 1,
      fill : (column, row, letter) => `${letter}:${column}:${row}`,
      x    : 0,
      y    : 0
    })
    const fills = Array.from(drawn.matchAll(/fill="([^"]+)"/gu), ([, fill]) => fill)

    expect([fills[0], fills.at(-1)]).toStrictEqual(['0:0:0', expect.stringMatching(/^1:/u)])
  })
})
