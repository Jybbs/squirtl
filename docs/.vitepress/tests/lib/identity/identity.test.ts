import { describe, expect, it } from 'vitest'

import * as identity from '../../../lib/identity/identity.ts'

describe('hexOf', () => {
  it.each([
    ['primary', identity.IDENTITY.colors.primary.hex],
    ['ground', identity.IDENTITY.neutrals.ground.hex],
    ['night', identity.IDENTITY.ramp.night.hex]
  ] as const)('reads %s from whichever table declares it', (token, hex) => {
    expect(identity.hexOf(token)).toBe(hex)
  })
})

describe('roleHue', () => {
  it.each([
    ['agent', 'denim'],
    ['random', 'seacaller'],
    ['starter', 'amethyst']
  ] as const)('reads the %s role in %s', (role, hue) => {
    expect(identity.roleHue(role)).toBe(hue)
  })
})

describe('spriteShades', () => {
  it('reads the Game Boy’s shades, lightest first, as the identity’s ground, pale, deep, and night', () => {
    expect(identity.spriteShades)
      .toStrictEqual((['ground', 'pale', 'deep', 'night'] as const).map(token => identity.hexOf(token)))
  })
})
