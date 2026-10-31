import { describe, expect, it } from 'vitest'

import { roleHue } from '../../../lib/identity/identity.ts'
import { hueOf }   from '../../../lib/widgets/chips.ts'

describe('hueOf', () => {
  it.each([
    [{ hue: 'fern', role: 'agent' }, 'fern'],
    [{ role: 'agent' }, roleHue('agent')],
    [{ hue: null, role: 'starter' }, roleHue('starter')],
    [{ role: 'none' }, null],
    [{}, null]
  ] as const)('reads the hue a chip showing %o takes as %s', (content, hue) => {
    expect(hueOf(content)).toBe(hue)
  })
})
