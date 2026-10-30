import { describe, expect, it } from 'vitest'

import { runsOf, spriteMarkup } from '../../../lib/drawing/sprites.ts'

/**
 * A frame four pixels square, a ring of the darkest shade around a blank pixel
 * it encloses, with a blank corner the edge reaches.
 */
const RING = ['0333', '3003', '3003', '3333']

describe('runsOf', () => {
  it('draws a blank pixel the sprite encloses and leaves out one the edge reaches', () => {
    expect(runsOf(RING)).toStrictEqual([
      { shade: 3, width: 3, x: 1, y: 0 },
      { shade: 3, width: 1, x: 0, y: 1 },
      { shade: 0, width: 2, x: 1, y: 1 },
      { shade: 3, width: 1, x: 3, y: 1 },
      { shade: 3, width: 1, x: 0, y: 2 },
      { shade: 0, width: 2, x: 1, y: 2 },
      { shade: 3, width: 1, x: 3, y: 2 },
      { shade: 3, width: 4, x: 0, y: 3 }
    ])
  })

  it('mirrors each row where the frame faces the other way', () => {
    expect(runsOf(RING, true)[0]).toStrictEqual({ shade: 3, width: 3, x: 0, y: 0 })
  })
})

describe('spriteMarkup', () => {
  it('draws each run as a rectangle in its shade, widened so no seam shows', () => {
    const placing = { fills: ['w', 'l', 'd', 'b'], opacity: 0.5, size: 2, x: 10, y: 20 }
    const markup  = spriteMarkup(['0000', '0300', '0000', '0000'], placing)

    expect(markup)
      .toBe('<g opacity="0.5"><rect x="12.00" y="22.00" width="2.30" height="2.30" fill="b"/></g>')
  })
})
