import fs from 'node:fs'

import { describe, expect, it } from 'vitest'

import readme                      from '../../../../.github/README.md?raw'
import { WALKING, walksOf }        from '../../../../docs/.vitepress/lib/front/learning.ts'
import { SCHEMES }                 from '../../../../docs/.vitepress/lib/identity/palette.ts'
import * as movie                  from '../../../../docs/.vitepress/lib/readme/movie.ts'
import * as preview                from '../../../../docs/.vitepress/lib/readme/preview.ts'
import { test }                    from '../../common/checkout.ts'
import { type Decoded, decodeGif } from '../../common/gif.ts'

/**
 * GitHub's page ground in each scheme, which the column of counts takes.
 */
const GROUNDS = { dark: 0x0d_11_17, light: 0xff_ff_ff } as const

/**
 * Reads the milliseconds `gif` plays for, once through.
 */
const lengthOf = (gif: Decoded): number => gif.delays.reduce((sum, delay) => sum + delay, 0) * 10

/**
 * One walk, the one after 50 episodes, which arrives in a handful of presses.
 */
const MOMENTS = walksOf({ ...WALKING, moments: [50] })

/**
 * The README's preview at a frame each second with no rest and the town at its
 * own pixels, so a case encodes and decodes a handful of small frames rather
 * than the hundreds the README carries.
 */
const QUICK: movie.Preview = { ...movie.PREVIEW, frame: 1000, rest: 0, scale: 1 }

describe('previewAlt', () => {
  test('describes the walks the preview plays in the sentence the README carries', () => {
    expect(readme).toContain(`alt="${preview.previewAlt()}"`)
  })

  test('names the last and the first walk by their episodes and presses', () => {
    expect(preview.previewAlt(walksOf({ ...WALKING, moments: [6, 50] }))).toMatch(
      /after 6 and 50 episodes .* after 50 episodes arriving in 18 presses and the walk after 6 in 204 presses/u
    )
  })
})

describe('previewPath', () => {
  it.each(SCHEMES)('holds the committed %s preview at the size the preview draws, within the 6 MB '
                 + 'guide', scheme => {
    const bytes  = fs.readFileSync(preview.previewPath(import.meta.url, scheme))
    const played = movie.previewMovie(import.meta.url, MOMENTS, movie.PREVIEW, scheme)

    expect([bytes.readUInt16LE(6), bytes.readUInt16LE(8)]).toStrictEqual([played.width, played.height])
    expect(bytes.length).toBeLessThanOrEqual(6_000_000)
  })
})

describe('writePreviews', () => {
  test('writes the preview in every scheme on its own ground, each looping forever on one '
     + 'palette', ({ checkout }) => {
    const { metaUrl } = checkout()

    preview.writePreviews(metaUrl, MOMENTS, QUICK)

    const decoded = SCHEMES.map(scheme => decodeGif(fs.readFileSync(preview.previewPath(metaUrl, scheme))))
    const length  = [...movie.previewMovie(metaUrl, MOMENTS, QUICK, 'light').frames()].length * QUICK.frame

    expect(decoded.map(gif => [gif.loops, gif.locals, lengthOf(gif), gif.frames[0]!.at(-1)]))
      .toStrictEqual(SCHEMES.map(scheme => [0, 0, length, GROUNDS[scheme]]))
  })
})
