import fs   from 'node:fs'
import path from 'node:path'

import { docsDir } from '../config/paths.ts'

/**
 * A line of the site's TypeScript running past `LINE_LIMIT`, under its path
 * from the root of the checkout and its number counted from 1, beside its
 * length in characters.
 */
export interface LongLine {
  file   : string
  length : number
  line   : number
}

/**
 * The characters a line of the site's TypeScript holds at most.
 */
export const LINE_LIMIT = 110

/**
 * Matches a line holding a regular expression literal or a glob string alone
 * after its indent, closed by any commas and parentheses, the one line no wrap
 * can bring under `LINE_LIMIT`.
 */
const WHOLE = /^\s*(?:\/(?![*/]).*\/[dgimsuvy]*|(['"`])[^'"`]*\*[^'"`]*\1)[),]*$/u

/**
 * Reads every TypeScript and TSX file under `docs/`, outside the packages Bun
 * installs, and returns each line running past `LINE_LIMIT` that `WHOLE` does
 * not match, in the order of its path and then its number.
 */
export function longLines(metaUrl: string): LongLine[] {
  const docs    = docsDir(metaUrl)
  const pattern = ['**/*.{ts,tsx}', '.vitepress/**/*.{ts,tsx}']
  return fs.globSync(pattern, { cwd: docs, exclude: ['node_modules/**'] })
    .toSorted()
    .flatMap(file => fs.readFileSync(path.join(docs, file), 'utf8')
      .split('\n')
      .flatMap((text, index) => {
        const length = [...text].length
        return length > LINE_LIMIT && !WHOLE.test(text)
          ? [{ file: `docs/${file}`, length, line: index + 1 }]
          : []
      }))
}

/**
 * Prints each of `lines` beside its file, its number, and its length.
 *
 * Returns:
 *   The exit status, 1 where any line runs past `LINE_LIMIT` and 0 otherwise.
 */
export function proveLines(lines: readonly LongLine[]): number {
  for (const { file, length, line } of lines) {
    console.error(
        `${file}:${line} runs ${length} characters, past the ${LINE_LIMIT} a line holds `
      + 'unless a regular expression or a glob stands alone on it'
    )
  }
  return lines.length > 0 ? 1 : 0
}
