import { describe, expect, it } from 'vitest'

import * as palettes from '../../../lib/game/palettes.ts'
import { hexOf }     from '../../../lib/identity/identity.ts'

/**
 * The red, green, and blue bytes of each color the town's light image holds,
 * from the lightest to the darkest.
 */
const SHADES = (['ground', 'pale', 'mid', 'deep'] as const)
  .map(token => Number.parseInt(hexOf(token).slice(1), 16))

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

describe('colorOf', () => {
  it('writes a color’s bytes as a hex, padding a dark one to six digits', () => {
    expect([palettes.colorOf(SHADES[0]!), palettes.colorOf(0x00_0a_0b)])
      .toStrictEqual([hexOf('ground'), '#000a0b'])
  })
})

describe('shadesOf and recolor', () => {
  it('ranks the town’s colors from the lightest to the darkest', () => {
    expect(palettes.shadesOf(PIXELS)).toStrictEqual(SHADES)
  })

  it('keeps no more colors than the Game Boy has shades', () => {
    expect(palettes.shadesOf(Uint8ClampedArray.from([...PIXELS, 1, 2, 3, 255]))).toHaveLength(4)
  })

  it.each([
    ['3210', ['ground', 'deep', 'pale', 'mid']],
    ['3333', ['deep', 'deep', 'deep', 'deep']],
    ['0000', ['ground', 'ground', 'ground', 'ground']],
    ['3321', ['pale', 'deep', 'mid', 'deep']]
  ] as const)('sets each color to the shade the palette %s gives it', (palette, tokens) => {
    const target = new Uint8ClampedArray(PIXELS.length)

    palettes.recolor(palette, SHADES, PIXELS, target)

    expect(hexesOf(target)).toStrictEqual(tokens.map(token => hexOf(token)))
  })
})
