import fs   from 'node:fs'
import path from 'node:path'

import { cacheDir } from './paths.ts'

/**
 * The share of the package's lines and branches its suite covers, as the
 * figure the README's coverage badge reads from the published site.
 */
interface Coverage {
  percent: string
}

/**
 * Writes `coverage.json` at the root of `outDir` from the report `py:coverage`
 * leaves under `.cache/coverage/` in the checkout holding `metaUrl`, holding
 * the total rounded to a whole percent, and writes nothing where no report
 * sits there.
 */
export function writeCoverage(outDir: string, metaUrl: string): void {
  const report = path.join(cacheDir(metaUrl, 'coverage'), 'coverage.json')
  if (!fs.existsSync(report)) return

  const { totals } = JSON.parse(fs.readFileSync(report, 'utf8')) as {
    totals: { percent_covered: number }
  }
  const figure: Coverage = { percent: totals.percent_covered.toFixed(0) }

  fs.writeFileSync(path.join(outDir, 'coverage.json'), `${JSON.stringify(figure)}\n`)
}
