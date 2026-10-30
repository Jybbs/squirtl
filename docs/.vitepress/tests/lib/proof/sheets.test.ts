import { describe, expect, it, vi } from 'vitest'

import { prove, siteSheets } from '../../../lib/proof/sheets.ts'

describe('siteSheets', () => {
  it('reads the utilities the components carry beside every other sheet of the theme', async () => {
    const sheets = await siteSheets(import.meta.url)

    expect(sheets[0]!.name).toBe('the utilities')
    expect(sheets.map(sheet => sheet.name)).toContain('theme/styles/roles.css')
    expect(sheets[0]!.css).toContain('--color-ground')
  })
})

describe('prove', () => {
  it('passes sheets setting no literal and fails on one, naming its sheet', () => {
    const error = vi.spyOn(console, 'error').mockImplementation(() => {})

    expect(prove([{ css: '.a { width: var(--spacing-4); }', name: 'clean' }])).toBe(0)
    expect(prove([{ css: '.a { width: 13px; }', name: 'theme/styles/odd.css' }])).toBe(1)
    expect(error).toHaveBeenCalledExactlyOnceWith(
      'theme/styles/odd.css sets width: 13px, which no theme variable supplies'
    )
  })
})
