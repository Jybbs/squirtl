import { describe, expect, it, vi } from 'vitest'

import { LINE_LIMIT, longLines, proveLines } from '../../../lib/proof/lines.ts'
import { test }                              from '../../common/checkout.ts'

/**
 * A line `length` characters long, the comment marks opening it.
 */
const comment = (length: number): string => `//${'x'.repeat(length - 2)}`

describe('longLines', () => {
  test('reads each TypeScript and TSX line past the limit under docs, outside '
     + 'node_modules', ({ checkout }) => {
    const { metaUrl } = checkout({
      'docs/.vitepress/lib/a.ts'    : `${comment(LINE_LIMIT)}\n${comment(LINE_LIMIT + 1)}\n`,
      'docs/.vitepress/theme/b.tsx' : `ok\n${comment(LINE_LIMIT + 3)}\n`,
      'docs/node_modules/c/d.ts'    : `${comment(LINE_LIMIT + 1)}\n`,
      'docs/pages/e.md'             : `${comment(LINE_LIMIT + 1)}\n`,
      'docs/pages/f.ts'             : `${comment(LINE_LIMIT + 2)}\n`,
      'docs/pages/g.tsx'            : `${comment(LINE_LIMIT + 4)}\n`
    })

    expect(longLines(metaUrl)).toStrictEqual([
      { file: 'docs/.vitepress/lib/a.ts', length: LINE_LIMIT + 1, line: 2 },
      { file: 'docs/.vitepress/theme/b.tsx', length: LINE_LIMIT + 3, line: 2 },
      { file: 'docs/pages/f.ts', length: LINE_LIMIT + 2, line: 1 },
      { file: 'docs/pages/g.tsx', length: LINE_LIMIT + 4, line: 1 }
    ])
  })

  test('counts a character outside the Basic Multilingual Plane once', ({ checkout }) => {
    const { metaUrl } = checkout({ 'docs/.vitepress/a.ts': `${'🎒'.repeat(LINE_LIMIT)}\n` })

    expect(longLines(metaUrl)).toStrictEqual([])
  })

  test.for([
    ['a regular expression alone', `  /${'a'.repeat(LINE_LIMIT)}/u,`, []],
    ['a glob alone', `  '**/${'a'.repeat(LINE_LIMIT)}*.ts')`, []],
    ['a regular expression beside a call', `  expect(text).toMatch(/${'a'.repeat(LINE_LIMIT)}/u)`, [1]],
    ['a string holding no glob', `  '${'a'.repeat(LINE_LIMIT)}'`, [1]],
    ['a comment closing on a slash', `  //${'a'.repeat(LINE_LIMIT)}/`, [1]],
    ['a block comment closing on a slash', `  /*${'a'.repeat(LINE_LIMIT)}*/`, [1]]
  ] as const)('reads %s past the limit as long or not', ([, text, lines], { checkout }) => {
    const { metaUrl } = checkout({ 'docs/.vitepress/a.ts': `${text}\n` })

    expect(longLines(metaUrl).map(({ line }) => line)).toStrictEqual(lines)
  })
})

describe('proveLines', () => {
  it('passes no long line and fails on one, naming its file, its number, and its length', () => {
    const error = vi.spyOn(console, 'error').mockImplementation(() => {})

    expect(proveLines([])).toBe(0)
    expect(proveLines([{ file: 'docs/.vitepress/a.ts', length: 112, line: 7 }])).toBe(1)
    expect(error).toHaveBeenCalledExactlyOnceWith(
        'docs/.vitepress/a.ts:7 runs 112 characters, past the 110 a line holds '
      + 'unless a regular expression or a glob stands alone on it'
    )
  })
})
