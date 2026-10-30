import { describe, expect, it } from 'vitest'

import * as tints   from '../../../../lib/front/learning/tints.ts'
import { IDENTITY } from '../../../../lib/identity/identity.ts'

describe('walkHuesOf', () => {
  it.each([
    [1, ['denim']],
    [4, ['amethyst', 'fern', 'heath', 'denim']],
    [5, ['seacaller', 'amethyst', 'fern', 'heath', 'denim']]
  ])('gives %i walks the agent’s hue for the latest and the next hue for each earlier', (walks, hues) => {
    expect(tints.walkHuesOf(walks)).toStrictEqual(hues)
  })
})

describe('fillsOf', () => {
  it.each(Object.keys(IDENTITY.hues) as (keyof typeof IDENTITY.hues)[])(
    'draws a sprite in %s from the screen’s white through its pale step and the hue to its deep step',
    hue => {
      const { light, token } = IDENTITY.hues[hue]

      expect(tints.fillsOf(hue)).toStrictEqual([
        IDENTITY.neutrals.ground.hex,
        light.pale,
        IDENTITY.colors[token as keyof typeof IDENTITY.colors].hex,
        light.deep
      ])
    }
  )
})

describe('blendsOf', () => {
  const fills  = [['#000000', '#000000'], ['#ffffff', '#ffffff'], ['#0000ff', '#0000ff']]
  const blends = tints.blendsOf(fills, 6)

  it('makes a crossfade for every stack of walks, and none for the stack holding no walk', () => {
    expect(blends).toHaveLength(8)
    expect(blends[0]).toStrictEqual([])
  })

  it('holds a stack of one walk at its own colors', () => {
    expect(new Set(blends[2]!.flat())).toStrictEqual(new Set(['#ffffff']))
  })

  it.each([
    [0, '#000000'],
    [1, '#808080'],
    [2, '#ffffff'],
    [3, '#8080ff'],
    [4, '#0000ff'],
    [5, '#000080']
  ])('steps a stack of three around its walks’ colors in turn, step %i at %s', (step, fill) => {
    expect(blends[7]![step]).toStrictEqual([fill, fill])
  })
})
