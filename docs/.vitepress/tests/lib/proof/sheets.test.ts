import { describe, expect, it, vi } from 'vitest'

import { prove, siteSheets } from '../../../lib/proof/sheets.ts'

describe('siteSheets', () => {
  it('reads the utilities the components carry beside every other sheet of the theme', async () => {
    const sheets = await siteSheets(import.meta.url)

    expect([sheets[0]!.name, sheets[0]!.handwritten]).toStrictEqual(['the utilities', false])
    expect(sheets.slice(1).map(sheet => [sheet.name, sheet.handwritten]))
      .toContainEqual(['theme/styles/roles.css', true])
    expect(sheets[0]!.css).toContain('--color-ground')
  })
})

describe('prove', () => {
  it('passes sheets setting no literal and fails on one, naming its sheet', () => {
    const error = vi.spyOn(console, 'error').mockImplementation(() => {})

    expect(prove([{ css: '.a { width: var(--spacing-4); }', handwritten: true, name: 'clean' }])).toBe(0)
    expect(prove([{ css: '.a { width: 13px; }', handwritten: true, name: 'theme/styles/odd.css' }])).toBe(1)
    expect(error).toHaveBeenCalledExactlyOnceWith(
      'theme/styles/odd.css sets width: 13px, which no theme variable supplies'
    )
  })

  it('reads a custom property’s own value in a sheet the theme writes by hand alone', () => {
    const error = vi.spyOn(console, 'error').mockImplementation(() => {})
    const css   = ':root { --vp-c-bg: #ffffff; }'

    const utilities = prove([{ css, handwritten: false, name: 'the utilities' }])
    const roles     = prove([{ css, handwritten: true, name: 'roles' }])

    expect([utilities, roles]).toStrictEqual([0, 1])
    expect(error).toHaveBeenCalledExactlyOnceWith(
      'roles sets --vp-c-bg: #ffffff, which no theme variable supplies'
    )
  })
})
