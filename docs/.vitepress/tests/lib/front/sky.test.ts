import { describe, expect, it } from 'vitest'

import * as sky     from '../../../lib/front/sky.ts'
import { hexOf }    from '../../../lib/identity/identity.ts'
import { Recorder } from '../../common/canvas.ts'

/**
 * A page a case lays the walk out on, a viewport tall, scrolled to the top,
 * with motion playing.
 */
const SCENE: sky.Scene = { height: 1200, quiet: [], scroll: 0, still: false, time: 0, view: 800, width: 420 }

describe('serpentine', () => {
  it('runs each row across the page and turns down to the next, running it the other way', () => {
    const walk    = sky.serpentine(SCENE.width, SCENE.height)
    const columns = Math.floor(SCENE.width / sky.SKY.pitch)

    expect(walk.slice(0, columns).map(([x]) => x))
      .toStrictEqual(Array.from({ length: columns }, (_, c) => c * 14 + 7))
    expect(new Set(walk.map(([x, y]) => `${x},${y}`)).size).toBe(walk.length)
  })

  it('lays at least one row on a page shorter than a row', () => {
    expect(sky.serpentine(140, 10)).toHaveLength(10)
  })
})

describe('branchesOf', () => {
  it('branches every few steps, more often on a wide page, each path kept inside the page', () => {
    const walk   = sky.serpentine(SCENE.width, SCENE.height)
    const wide   = sky.branchesOf(walk, 900)
    const narrow = sky.branchesOf(walk, SCENE.width)
    const across = narrow.flatMap(branch => branch.points.map(([x]) => x))

    expect([wide[1]!.at - wide[0]!.at, narrow[1]!.at - narrow[0]!.at]).toStrictEqual([3, 5])
    expect([Math.min(...across), Math.max(...across)]).toStrictEqual([7, SCENE.width - 7])
  })
})

describe('headOf', () => {
  it.each([
    [0, 0.4 * 5],
    [400, (400 + 480) / 1200 * 5],
    [10000, 5]
  ])('runs the head to the step level with 0.6 of a viewport scrolled %i pixels down', (scroll, step) => {
    expect(sky.headOf([[0, 0], [0, 1], [0, 2], [0, 3], [0, 4]], { ...SCENE, scroll })).toBeCloseTo(step, 6)
  })
})

describe('flicker', () => {
  it('holds a dot at full strength while motion is off and between 0.72 and 1 while it plays', () => {
    const playing = Array.from({ length: 50 }, (_, t) => sky.flicker({ still: false, time: t / 3 }, 7, 3))

    expect(sky.flicker({ still: true, time: 4 }, 7, 3)).toBe(1)
    expect(Math.min(...playing)).toBeGreaterThanOrEqual(0.72)
    expect(Math.max(...playing)).toBeLessThanOrEqual(1)
  })
})

describe('paintSky', () => {
  it('draws the walk to its head with the head in the strong tone, and dims dots behind words', () => {
    const recorder = new Recorder()
    const walk     = [[7, 10], [21, 10], [35, 10]] as const
    const quiet    = [{ bottom: 20, left: 14, right: 28, top: 0 }]

    sky.paintSky(recorder, [], 2, { ...SCENE, quiet }, sky.TONES.light, walk)

    expect(recorder.arcs.map(arc => [arc.x, arc.fill, arc.radius > 4])).toStrictEqual([
      [7, hexOf('deep'), false], [21, hexOf('deep'), false], [35, hexOf('deep'), true]
    ])
    expect(recorder.arcs[1]!.alpha).toBeCloseTo(recorder.arcs[0]!.alpha * sky.SKY.quiet, 1)
  })

  it('grows each side path the head has passed and skips a dot outside the viewport', () => {
    const recorder = new Recorder()
    const branch   = { at: 0, points: [[7, 10], [7, 24], [7, 2000]] as const }
    const walk     = [[7, 10], [7, 24], [7, 38], [7, 52], [7, 66]] as const

    sky.paintSky(recorder, [branch, { at: 99, points: [] }], 4, SCENE, sky.TONES.dark, walk)
    const grown = recorder.arcs.filter(arc => arc.radius === 1.7).map(arc => arc.fill)

    expect(grown.filter(fill => fill === sky.TONES.dark.dot)).toHaveLength(1)
  })

  it('draws the whole walk with no head where motion is off', () => {
    const recorder = new Recorder()
    const branches = [{ at: 0, points: [[7, 10], [7, 24]] as const }]

    sky.paintSky(recorder, branches, 0, { ...SCENE, still: true }, sky.TONES.light, [[7, 10], [21, 10]])

    expect([recorder.arcs.length, recorder.globalAlpha]).toStrictEqual([3, 1])
  })
})

describe('quietOf', () => {
  it('places each box of words on the page, widened on every side by the dimming margin', () => {
    expect(sky.quietOf([{ bottom: 40, left: 10, right: 90, top: 20 }], 300))
      .toStrictEqual([{ bottom: 356, left: -6, right: 106, top: 304 }])
  })
})
