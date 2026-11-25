import { describe, expect, it } from 'vitest'

import { type Scheme, contrast } from '../../../../docs/.vitepress/lib/identity/identity.ts'
import themeSheet                from '../../../../docs/.vitepress/lib/rendered/theme.css?raw'
import rolesSheet                from '../../../../docs/.vitepress/theme/styles/roles.css?raw'

/**
 * The 4.5:1 WCAG 2.2 sets for body text against the ground it sits on.
 */
const TEXT = 4.5

/**
 * Lists each custom property `css` declares beside its value.
 */
const declared = (css: string): [string, string][] =>
  [...css.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/gu)].map(([, name, value]) => [name!, value!.trim()])

/**
 * The variables the theme maps the default theme's own onto, and every theme
 * variable the identity sets, each beside its value.
 */
const roles  = declared(rolesSheet)
const tokens = new Map([...declared(themeSheet), ...roles])

/**
 * Lists the variables `roles.css` declares whose names match `pattern`.
 */
const named = (pattern: RegExp): string[] => roles.map(([name]) => name).filter(name => pattern.test(name))

/**
 * Reads the hex the variable `name` takes in `scheme`, through every `var()` it
 * reads and the side of a `light-dark()` the scheme takes.
 */
function resolved(name: string, scheme: Scheme): string {
  const value  = tokens.get(name) ?? ''
  const read   = /^var\((--[\w-]+)\)$/u.exec(value)
  const paired = /^light-dark\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)$/u.exec(value)
  if (read) return resolved(read[1]!, scheme)
  return paired ? paired[scheme === 'light' ? 1 : 2]! : value
}

describe('roles.css', () => {
  const grounds = named(/^--vp-c-bg/u)
  const inks    = named(/^--vp-c-(?:text-\d|brand-[12])$/u)

  it.for((['dark', 'light'] as const).flatMap(scheme =>
    inks.flatMap(ink => grounds.map(ground => [scheme, ink, ground] as const))
  ))('holds %s %s to the contrast for text on %s', ([scheme, ink, ground]) => {
    expect(contrast(resolved(ink, scheme), resolved(ground, scheme))).toBeGreaterThanOrEqual(TEXT)
  })

  it.for((['dark', 'light'] as const).flatMap(scheme =>
    named(/^--vp-button-brand(?:-\w+)?-text$/u).map(label => [scheme, label] as const)
  ))('holds a brand button’s label in %s, %s, to the contrast for text on its fill', ([scheme, label]) => {
    const fill = label.replace(/-text$/u, '-bg')

    expect(contrast(resolved(label, scheme), resolved(fill, scheme))).toBeGreaterThanOrEqual(TEXT)
  })

  it.for(['dark', 'light'] as const)('sets inline code in %s on its own ground, holding its text', scheme => {
    const ground = resolved('--vp-code-bg', scheme)

    expect(ground).not.toBe(resolved('--vp-c-bg', scheme))
    expect(contrast(resolved('--vp-code-color', scheme), ground)).toBeGreaterThanOrEqual(TEXT)
  })

  it('sets inline code at the identity’s code size, standing its x-height at the body’s', () => {
    const sizes = [tokens.get('--vp-code-font-size'), tokens.get('--text-code')]

    expect(sizes).toStrictEqual(['var(--text-code)', '0.9218em'])
  })

  it('reads a hex for every color it measures', () => {
    const colors = [
      ...named(/^--vp-(?:c-(?:bg|text|brand-[12]$)|code-(?:bg|color))/u),
      ...named(/^--vp-button-brand/u)
    ]

    const hexes = (['dark', 'light'] as const).flatMap(scheme => colors.map(name => resolved(name, scheme)))

    expect(hexes.filter(hex => !/^#[\da-f]{6}$/u.test(hex))).toStrictEqual([])
  })
})
