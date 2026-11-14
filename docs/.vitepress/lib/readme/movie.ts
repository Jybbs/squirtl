import type { Moment }         from '../front/learning.ts'
import * as transition         from '../front/learning/transition.ts'
import { Walks }               from '../front/learning/walks.ts'
import type { Scheme }         from '../identity/identity.ts'
import { REST }                from '../widgets/autoplay.ts'
import type { Movie }          from './gif.ts'
import * as raster             from './raster.ts'
import { type Tally, tallyOf } from './tally.ts'

/**
 * How the README's preview plays the walks: the milliseconds each frame holds,
 * the rest after the last walk ends before the encounter, the times the town
 * is drawn at, and the column of counts beside it.
 */
export interface Preview {
  frame : number
  rest  : number
  scale : number
  tally : Tally
}

/**
 * The preview as the README carries it, a frame each 20 ms, the widget's own
 * rest, and the town at twice its pixels beside a column of 240.
 */
export const PREVIEW: Preview = {
  frame : 20,
  rest  : REST,
  scale : 2,
  tally : {
    figure : { size: 22, y: 42 },
    inset  : 12,
    label  : { size: 13, y: 12 },
    left   : 40,
    pitch  : 70,
    rule   : { height: 46, width: 3 },
    top    : 26,
    width  : 240,
    word   : { gap: 8, size: 13 }
  }
}

/**
 * Packs the RGBA pixels of `pixels` as one number each, its red, green, and
 * blue bytes.
 */
function packed(pixels: ArrayLike<number>): Uint32Array {
  return Uint32Array.from({ length: pixels.length / 4 }, (_, at) =>
    pixels[4 * at]! << 16 | pixels[4 * at + 1]! << 8 | pixels[4 * at + 2]!)
}

/**
 * Plays `walks` as the widget's autoplay does, a press each `walks.play.press`
 * milliseconds, a rest once the last walk ends, and then the encounter, whose
 * double circle sets every walk back at his door, stepping the clock a frame
 * at a time until the encounter ends.
 *
 * Yields:
 *   The press of the clock each frame shows, once `walks` stands at that frame.
 */
function* playing(walks: Walks, phases: transition.Phases, preview: Preview): Generator<number> {
  const { press } = walks.play
  const start     = walks.longest * press + preview.rest
  let at          = 0
  let now         = 0
  const events    = [
    ...Array.from({ length: walks.longest }, (_, n) => [n * press, () => {
      walks.set(n + 1, press)
      at = n + 1
    }] as const),
    [start, () => walks.encounter(() => {
      walks.set(0)
      at = 0
    })] as const
  ]
  for (let time = 0; time < start + phases.end; time += preview.frame) {
    while (events.length > 0 && events[0]![0] <= time) {
      const [when, act] = events.shift()!
      walks.advance(when - now)
      now = when
      act()
    }
    walks.advance(time - now)
    now = time
    yield at
  }
}

/**
 * Plays the walks `moments` hold as the README's preview in `scheme`, Pallet
 * Town at `preview.scale` times its pixels as the widget plays it, beside the
 * column of each walk's count on GitHub's ground.
 *
 * Args:
 *   metaUrl : The `import.meta.url` of the module calling, which the checkout
 *     holding the faces is found from.
 *   moments : The walks the town plays.
 *   preview : How the preview plays and sets the counts.
 *   scheme  : The scheme the column of counts is drawn in.
 */
export function previewMovie(
  metaUrl : string,
  moments : readonly Moment[],
  preview : Preview,
  scheme  : Scheme
): Movie {
  const { scale, tally } = preview
  const view             = transition.VIEW
  const town             = raster.townIn(metaUrl, view)
  const [width, height]  = [view.width * scale + tally.width, view.height * scale]
  const columns          = new Map<number, Uint32Array>()

  return {
    delay  : preview.frame,
    height : height,
    width  : width,
    frames : function* () {
      const walks  = new Walks(moments)
      const grid   = new raster.Raster(view.width, view.height)
      const frame  = new Uint32Array(width * height)
      for (const at of playing(walks, transition.battlePhases, preview)) {
        walks.draw(grid, town)
        const pixels = packed(grid.view.data)
        for (let y = 0; y < height; y++) {
          for (let x = 0; x < view.width * scale; x++) {
            frame[y * width + x] = pixels[Math.floor(y / scale) * view.width + Math.floor(x / scale)]!
          }
        }
        const column = columns.getOrInsertComputed(at, () =>
          packed(raster.svgPixels(metaUrl, tallyOf(at, height, scheme, tally, walks))))
        for (let y = 0; y < height; y++) {
          frame.set(column.subarray(y * tally.width, (y + 1) * tally.width), y * width + view.width * scale)
        }
        yield frame
      }
    }
  }
}
