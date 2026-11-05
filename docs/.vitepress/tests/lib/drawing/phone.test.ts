import { describe, expect, it } from 'vitest'

import { cell, lone, opener } from '../../../lib/drawing/phone.ts'

/**
 * Reads the width of the first drawing `html` holds.
 */
function drawnWidth(html: string): number {
  return Number(/width="(\d+)"/u.exec(html)![1])
}

describe('the phones', () => {
  it.each([
    ['a run of two', [1, 3], 30],
    ['a run of three', [1, 3, 5], 42],
    ['a single digit beside two digits', [1, 11], 37],
    ['two pairs of digits', [11, 13], 44]
  ])('sizes the slab of %s from its numerals, a bar of one pixel at each join', (_, numbers, width) => {
    expect(drawnWidth(cell(numbers[0]!, numbers, 0))).toBe(width)
  })

  it('draws the slab and the lens in the first cell alone', () => {
    expect(cell(1, [1, 3], 0)).toContain('<svg')
    expect(cell(3, [1, 3], 1)).not.toContain('<svg')
  })

  it('widens the cell of a number of two digits', () => {
    expect(cell(11, [1, 11], 1)).toContain('footnote-wide')
    expect(cell(1, [1, 11], 0)).not.toContain('footnote-wide')
  })

  it.each([
    ['a lone marker', lone(7)],
    ['an opener', opener(7)]
  ])('writes %s holding its number and hiding its drawing', (_, html) => {
    expect(html).toContain('<span class="footnote-numeral">7</span>')
    expect(html).toContain('aria-hidden="true"')
  })
})
