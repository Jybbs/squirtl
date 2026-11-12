import { describe, expect, it } from 'vitest'

import { IDENTITY, contrast } from '../../../lib/identity/identity.ts'
import * as palette           from '../../../lib/identity/palette.ts'

/**
 * The named color whose token is `token`.
 */
const named = (token: string): palette.Named => palette.NAMED.find(each => each.token === token)!

describe('NAMED', () => {
  it('lists every color each table declares, in the order of the tables', () => {
    const tables = palette.TABLES.flatMap(({ table }) => Object.keys(IDENTITY[table]))

    expect(palette.NAMED.map(each => each.token)).toStrictEqual(tables)
  })
})

describe('GROUNDS', () => {
  it('reads each scheme’s ground from the color its scheme names', () => {
    expect(palette.GROUNDS).toStrictEqual({
      dark  : { hex: IDENTITY.neutrals.dark.hex, name: IDENTITY.neutrals.dark.name },
      light : { hex: IDENTITY.neutrals.ground.hex, name: IDENTITY.neutrals.ground.name }
    })
  })
})

describe('hueOfToken', () => {
  it.each([['primary', 'denim'], ['ground', null]] as const)('finds the hue whose color %s is as %s', (token, hue) => {
    expect(palette.hueOfToken(token)).toBe(hue)
  })
})

describe('stepsOf', () => {
  it('lists the ramp’s four shades from nearest the ground and then its text step', () => {
    const ramp = IDENTITY.hues.fern.dark

    expect(palette.stepsOf('fern', 'dark')).toStrictEqual([
      ...ramp.shades.map((hex, n) => ({ hex, name: `Shade ${n + 1}` })),
      { hex: ramp.text, name: 'Text' }
    ])
  })
})

describe('levelOf', () => {
  it.each([
    ['#000000', '#ffffff', 'text'],
    ['#949494', '#ffffff', 'mark'],
    ['#eeeeee', '#ffffff', 'fill']
  ] as const)('places %s on %s at %s', (hex, ground, level) => {
    expect(palette.levelOf(contrast(hex, ground))).toBe(level)
  })
})

describe('inkOn', () => {
  it('chooses whichever ground stands farther from the fill', () => {
    expect([palette.inkOn('#000000'), palette.inkOn('#ffffff')]).toStrictEqual([palette.GROUNDS.light.hex, palette.GROUNDS.dark.hex])
  })
})

describe('meterOf', () => {
  it.each([[1, 0], [21, 1]])('places a ratio of %d at %d along the meter', (ratio, share) => {
    expect(palette.meterOf(ratio)).toBeCloseTo(share)
  })
})

describe('blueFills', () => {
  it('fills Blue from the ground through the second shade and the hue’s mark to its text step', () => {
    const ramp = IDENTITY.hues.heath.light

    expect(palette.blueFills('heath', 'light'))
      .toStrictEqual([palette.GROUNDS.light.hex, ramp.shades[1], IDENTITY.marks.heath.light, ramp.text])
  })

  it('stands every fill apart from the one beside it', () => {
    for (const scheme of palette.SCHEMES) {
      const fills = palette.blueFills('denim', scheme)
      expect(fills.slice(1).every((fill, n) => contrast(fill, fills[n]!) > 1)).toBe(true)
    }
  })
})

describe('shownOf', () => {
  it('shows the color itself where no step is picked', () => {
    expect(palette.shownOf(named('primary'), null)).toStrictEqual({ hex: IDENTITY.colors.primary.hex, name: IDENTITY.colors.primary.name, what: 'primary' })
  })

  it('shows the color itself where its hue carries no ramp, whatever step is picked', () => {
    expect(palette.shownOf(named('ground'), 'light-0')).toMatchObject({ hex: IDENTITY.neutrals.ground.hex, what: 'ground' })
  })

  it('shows the step picked, named for the color and the step, on its ground', () => {
    expect(palette.shownOf(named('primary'), 'dark-4')).toStrictEqual({
      hex  : IDENTITY.hues.denim.dark.text,
      name : `${IDENTITY.colors.primary.name} Text`,
      what : `on ${palette.GROUNDS.dark.name}`
    })
  })
})

describe('STEPS', () => {
  it('names five steps on each ground, the light ground first', () => {
    expect(palette.STEPS).toStrictEqual(['light-0', 'light-1', 'light-2', 'light-3', 'light-4', 'dark-0', 'dark-1', 'dark-2', 'dark-3', 'dark-4'])
  })
})
