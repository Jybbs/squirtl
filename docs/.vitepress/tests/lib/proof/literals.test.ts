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
    ['@media (width < 40rem) { .a { margin: 2px; } }', 'margin: 2px']
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
    ['a property named for white space', '.a { white-space: nowrap; }']
  ])('passes %s', (_, css) => {
    expect(literals(css)).toStrictEqual([])
  })
})
