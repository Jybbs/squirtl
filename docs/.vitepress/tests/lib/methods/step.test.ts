import { describe, expect, it } from 'vitest'

import * as step from '../../../lib/methods/step.ts'

describe('STEPS', () => {
  it('walks the bedroom floor and back, each change of direction a step that only turns Blue', () => {
    expect(step.STEPS.map(each => [each.press, each.from, each.move])).toStrictEqual([
      ['right', [3, 6], null],
      ['right', [3, 6], [1, 0]],
      ['up', [4, 6], null],
      ['up', [4, 6], [0, -1]],
      ['a', [4, 5], null],
      ['down', [4, 5], null],
      ['down', [4, 5], [0, 1]],
      [null, [4, 6], null],
      ['left', [4, 6], null],
      ['left', [4, 6], [-1, 0]]
    ])
  })

  it('moves the read between frame 1 and frame 2 from one step to the next', () => {
    expect(step.STEPS.map(each => each.read)).toStrictEqual([1, 2, 1, 2, 1, 2, 1, 2, 1, 2])
  })

  it('scrolls a walk two pixels a pass from the read, a square by the last frame', () => {
    expect(step.STEPS[1]!.frames.map(frame => frame.pixels)).toStrictEqual([0, 0, 2, 2, 4, 4, 6, 6, 8, 8, 10, 10, 12, 12, 14, 14, 16])
  })

  it('turns Blue in place on the pass after the read of a step that only turns him', () => {
    expect(step.STEPS[2]!.frames.map(frame => [frame.facing, frame.stance]).slice(0, 5)).toStrictEqual([
      ['right', 'standing'], ['right', 'standing'], ['right', 'standing'], ['up', 'standing'], ['up', 'standing']
    ])
  })

  it('walks partway through a square in the walking frame, alternating feet down the rows', () => {
    expect(step.STEPS[6]!.frames.map(frame => frame.stance)).toContain('walking')
  })
})

describe('the sheet', () => {
  it('centers the view on Blue’s pixels into his walk', () => {
    expect([step.viewAt(step.STEPS[1]!, 1), step.viewAt(step.STEPS[1]!, 10), step.viewAt(step.STEPS[1]!, 17)])
      .toStrictEqual([[3, 6], [3.5, 6], [4, 6]])
  })

  it.each([
    [0, { f: 1, s: 0 }],
    [16, { f: 17, s: 0 }],
    [169, { f: 17, s: 9 }]
  ])('reads position %i as its step and frame', (at, cell) => {
    expect(step.cellOf(at)).toStrictEqual(cell)
  })

  it('describes a position by its step, its press, and its frame', () => {
    expect([step.describe(0), step.describe(119)]).toStrictEqual(['Step 1, Right, frame 1 of 17', 'Step 8, No press, frame 1 of 17'])
  })

  it.each([
    [20, 3, 0.5],
    [20, 16, 1],
    [20, 20, 1],
    [20, 21, 0.14]
  ])('at %i shows cell %i at strength %f', (at, cell, strength) => {
    expect(step.strengthOf(at, cell)).toBe(strength)
  })
})
