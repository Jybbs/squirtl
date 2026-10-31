import { describe, expect, it } from 'vitest'

import * as logo from '../../../lib/marks/logo.ts'

/**
 * The colors of the trail's thirds on each ground, from the oldest to the
 * newest, as the identity records them.
 */
const THIRDS = {
  dark  : ['#294e95', '#3d6fd0', '#92b1e8'],
  light : ['#7097df', '#3d6fd0', '#294e95']
}

/**
 * Reads the dots of the mark `text` lays out that take `kind`.
 */
const dotsOf = <K extends logo.Dot['kind']>(text: string, kind: K): (logo.Dot & { kind: K })[] =>
  logo.markOf(text).dots.filter((dot): dot is logo.Dot & { kind: K } => dot.kind === kind)

/**
 * Whether the center of `dot` lies inside the square of `block`.
 */
const under = (dot: logo.Dot, block: logo.Block): boolean =>
  dot.x > block.x && dot.x < block.x + block.side && dot.y > block.y && dot.y < block.y + block.side

describe('markOf', () => {
  it.each([
    ['RL', { height: 620, width: 1020, x: -10, y: 90 }],
    ['SquiRtL', { height: 820, width: 3720, x: -10, y: -10 }]
  ])('frames %s at the outer edges of its dots', (text, view) => {
    expect(logo.markOf(text).view).toEqual(view)
  })

  it.each([
    { frame: 3, letter: 'R', mirror: false, stand: 0, x: -10, y: 90 },
    { frame: 5, letter: 'L', mirror: true, stand: 2, x: 590, y: 490 }
  ])('sets Blue in the $letter walking in frame $frame and standing in frame $stand', ({ x, y, ...walk }) => {
    expect(logo.markOf('RL').blocks.find(block => block.letter === walk.letter)).toEqual({
      ...walk,
      radius : 60,
      side   : 220,
      sprite : { size: 11.5, x: x + 18, y: y + 18 },
      x      : x,
      y      : y
    })
  })

  it('leaves out every dot under a block', () => {
    const { blocks, dots } = logo.markOf('SquiRtL')
    expect(dots.filter(dot => blocks.some(block => under(dot, block)))).toEqual([])
  })

  it('sets the name on the baseline seven cells down, each character where its advance reaches', () => {
    const { baseline, lefts } = logo.markOf('SquiRtL')
    expect([baseline, lefts]).toEqual([700, [0, 600, 1200, 1800, 2100, 2700, 3300]])
  })

  it('fails on text holding neither the R nor the L', () => {
    expect(() => logo.markOf('Squit')).toThrow('Squit holds none of the letters RL Blue walks through')
  })
})

describe('markOf, the trail', () => {
  it('walks the route from the top of the R to the foot of the L in steps of one', () => {
    const trail = dotsOf('RL', 'trail')
    const steps = trail.map(dot => dot.step).toSorted((a, b) => a - b)
    expect(steps).toEqual(Array.from({ length: 26 }, (_, step) => step))
    expect(trail.find(dot => dot.step === 0)).toMatchObject({ letter: 'R', third: 0, x: 250, y: 150 })
    expect(trail.find(dot => dot.step === 25)).toMatchObject({ letter: 'L', third: 2, x: 750, y: 450 })
  })

  it('splits the route into thirds of nine, eight, and nine dots', () => {
    const trail = dotsOf('SquiRtL', 'trail')
    expect([0, 1, 2].map(third => trail.filter(dot => dot.third === third).length)).toEqual([9, 8, 9])
  })

  it('leaves one dot ahead of Blue, between his block in the L and the Poké Ball', () => {
    expect(dotsOf('RL', 'ahead')).toEqual([{ index: 1, kind: 'ahead', letter: 'L', x: 850, y: 650 }])
  })

  it('sets the Poké Ball on the last dot of the L, ninety-two units across', () => {
    const { ball, dots } = logo.markOf('RL')
    expect(ball).toEqual({ index: 1, size: 5.75, x: 904, y: 604 })
    expect(dots.map(dot => [dot.x, dot.y])).not.toContainEqual([950, 650])
  })

  it('lights the R and the L alone with no ink, and every other letter of the name in ink', () => {
    expect(dotsOf(logo.logoLetters, 'ink')).toEqual([])
    const letters = new Set(dotsOf('SquiRtL', 'ink').map(dot => dot.letter))
    expect(letters).toEqual(new Set(['S', 'q', 'u', 'i', 't']))
  })
})

describe('paintOf', () => {
  it.each(['dark', 'light'] as const)('paints each third of the trail on the %s ground', scheme => {
    const paints = dotsOf('SquiRtL', 'trail').map(dot => [dot.third, logo.paintOf(dot, scheme)])
    expect(paints).toEqual(dotsOf('SquiRtL', 'trail').map(dot => [dot.third, THIRDS[scheme][dot.third]]))
  })

  it.each([
    ['dark', 'ahead', '#162d5b'],
    ['light', 'ahead', '#92b1e8'],
    ['dark', 'ink', '#f3f4f7'],
    ['light', 'ink', '#121722']
  ] as const)('paints each dot on the %s ground that is %s in %s', (scheme, kind, hex) => {
    expect(new Set(dotsOf('SquiRtL', kind).map(dot => logo.paintOf(dot, scheme)))).toEqual(new Set([hex]))
  })
})
