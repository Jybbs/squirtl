import { describe, expect, it } from 'vitest'

import * as sections from '../../../lib/config/sections.ts'
import { IDENTITY }  from '../../../lib/identity/identity.ts'
import { METHODS }   from '../../common/sections.ts'

/**
 * Two sections a case declares, in the alphabetical order the registry keeps.
 */
const DECLARED = [{ about: ['Each command,', 'and every setting.'], name: 'Commands' }, METHODS] as const

describe('SECTIONS', () => {
  it('ships no section until a page opens one', () => {
    expect(sections.SECTIONS).toStrictEqual([])
  })
})

describe('placed', () => {
  it('gives each section the hue its folder takes and the badge the game awards next', () => {
    const rows = sections.placed(DECLARED)
      .map(({ badge, folder, hue, index }) => [folder, hue, badge.name, index])

    expect(rows).toStrictEqual([
      ['commands', 'forest', IDENTITY.badges[0]!.name, 0],
      ['methods', 'indigo', IDENTITY.badges[1]!.name, 1]
    ])
  })
})

describe('sectionOf', () => {
  it.each([
    [{ relativePath: 'methods/agent.md' }, 'Methods'],
    [{ relativePath: 'commands/index.md' }, 'Commands'],
    [{ relativePath: 'index.md' }, undefined],
    [{ relativePath: 'results/curve.md' }, undefined],
    [{ isNotFound: true, relativePath: 'methods/missing.md' }, undefined]
  ])('reads the section %o sits in as %s', (page, name) => {
    expect(sections.sectionOf(page, DECLARED)?.name).toBe(name)
  })
})
