import fs   from 'node:fs'
import path from 'node:path'

import { describe, expect } from 'vitest'

import { docsDir }                 from '../../../lib/config/paths.ts'
import { WALKING, walksOf }        from '../../../lib/front/learning.ts'
import { SCHEMES }                 from '../../../lib/identity/palette.ts'
import * as movie                  from '../../../lib/readme/movie.ts'
import * as preview                from '../../../lib/readme/preview.ts'
import { test }                    from '../../common/checkout.ts'
import { type Decoded, decodeGif } from '../../common/gif.ts'

/**
 * Reads the milliseconds `gif` plays for, once through.
 */
const lengthOf = (gif: Decoded): number => gif.delays.reduce((sum, delay) => sum + delay, 0) * 10

/**
 * One walk, the one after 50 episodes, which arrives in a handful of presses.
 */
const MOMENTS = walksOf({ ...WALKING, moments: [50] })

/**
 * The README's preview at a frame each 200 ms with no rest, so a case decodes a
 * few dozen frames rather than the hundreds the README carries.
 */
const QUICK: movie.Preview = { ...movie.PREVIEW, frame: 200, rest: 0 }

describe('previewAlt', () => {
  test('describes the walks the preview plays in the sentence the README carries', () => {
    const readme = fs.readFileSync(path.join(docsDir(import.meta.url), '..', '.github', 'README.md'), 'utf8')

    expect(readme).toContain(`alt="${preview.previewAlt()}"`)
  })

  test('names the fastest and the slowest walk by their episodes and presses', () => {
    expect(preview.previewAlt(walksOf({ ...WALKING, moments: [6, 50] }))).toMatch(
      /after 6 and 50 episodes .* after 50 episodes arriving in 18 presses and the walk after 6 in 204 presses/u
    )
  })
})

describe('writePreviews', () => {
  test('writes the preview in every scheme, each looping forever on one palette', ({ checkout }) => {
    const { metaUrl } = checkout()

    preview.writePreviews(metaUrl, MOMENTS, QUICK)

    const docs    = docsDir(metaUrl)
    const decoded = SCHEMES.map(scheme => decodeGif(fs.readFileSync(path.join(docs, preview.previewPath(scheme)))))
    const played  = [...movie.previewMovie(metaUrl, MOMENTS, QUICK, 'light').frames()].length

    expect(decoded.map(gif => [gif.loops, gif.locals, lengthOf(gif)]))
      .toStrictEqual(SCHEMES.map(() => [0, 0, played * QUICK.frame]))
  })
})
