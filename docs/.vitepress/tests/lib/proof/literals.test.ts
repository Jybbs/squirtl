import { describe, expect, it } from 'vitest'

import { literals } from '../../../lib/proof/literals.ts'

describe('literals', () => {
  it.each([
    ['.a { width: 13px; }', 'width: 13px'],
    ['.a { transition: opacity 150ms; }', 'transition: opacity 150ms'],
    ['.a { color: #bada55; }', 'color: #bada55'],
    ['.a { color: rgb(0 0 0); }', 'color: rgb(0 0 0)'],
    ['.a { color: rebeccapurple; }', 'color: rebeccapurple'],
    ['.a { transition-timing-function: ease-in-out; }', 'transition-timing-function: ease-in-out'],
    ['.a { animation-timing-function: steps(4); }', 'animation-timing-function: steps(4)'],
    ['@media (width < 40rem) { .a { margin: 2px; } }', 'margin: 2px'],
    ['.a { font-family: Arial, sans-serif; }', 'font-family: Arial, sans-serif'],
    ['.a { font: italic 1em "Comic Sans MS"; }', 'font: italic 1em "Comic Sans MS"']
  ])('reports %s', (css, declaration) => {
    expect(literals(css)).toStrictEqual([declaration])
  })

  it.each([
    ['a theme variable', '.a { width: var(--spacing-mark); }'],
    ['a fallback inside a variable', '.a { color: var(--color-ink, #000); }'],
    ['a zero', '.a { margin: 0; inset: 0px; }'],
    ['a percentage and a keyword', '.a { width: 100%; color: currentColor; height: auto; }'],
    ['a mix of variables', '.a { color: color-mix(in oklch, var(--color-ink) 6%, var(--color-ground)); }'],
    ['a custom property', ':root { --spacing-4: 1rem; }'],
    ['a query width', '@container (width >= 44rem) { .a { display: grid; } }'],
    ['an @property registration', '@property --tw-shadow { syntax: "*"; initial-value: 0 0 #0000; }'],
    ['a fully rounded corner', '.a { border-radius: calc(infinity * 1px); }'],
    ['a comment', '/* width: 13px; */ .a { display: block; }'],
    ['a gradient', '.a { background-image: linear-gradient(var(--color-ink), var(--color-ground)); }'],
    ['a property named for white space', '.a { white-space: nowrap; }'],
    ['a face read from a variable', '.a { font-family: var(--font-display); }'],
    ['a face deferring to its parent', '.a { font-family: inherit; }']
  ])('passes %s', (_, css) => {
    expect(literals(css)).toStrictEqual([])
  })

  it.each([
    ['a hex', ':root { --vp-c-bg: #ffffff; }', '--vp-c-bg: #ffffff'],
    ['a face', ':root { --vp-font-family-mono: Menlo; }', '--vp-font-family-mono: Menlo']
  ])('reports a custom property holding %s in a sheet written by hand alone', (_, css, declaration) => {
    expect([literals(css), literals(css, true)]).toStrictEqual([[], [declaration]])
  })

  it('passes a custom property reading a theme variable in a sheet written by hand', () => {
    const css = ':root { --vp-c-bg: var(--color-ground); --vp-font-family-base: var(--font-body); }'

    expect(literals(css, true)).toStrictEqual([])
  })
})
