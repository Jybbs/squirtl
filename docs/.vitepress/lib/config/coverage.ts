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
 * Reads the total the report `py:coverage` leaves under `.cache/coverage/` in
 * the checkout holding `metaUrl` holds, rounded to a whole percent, or nothing
 * where no report sits there.
 */
export function coverageOf(metaUrl: string): string | undefined {
  const report = path.join(cacheDir(metaUrl, 'coverage'), 'coverage.json')
  if (!fs.existsSync(report)) return undefined

  const { totals } = JSON.parse(fs.readFileSync(report, 'utf8')) as {
    totals: { percent_covered: number }
  }
  return totals.percent_covered.toFixed(0)
}

/**
 * Writes `coverage.json` at the root of `outDir` holding the whole percent
 * `percent` the suite's last report measured, and writes nothing where no
 * report measured one.
 */
export function writeCoverage(outDir: string, percent: string | undefined): void {
  if (percent === undefined) return

  const figure: Coverage = { percent }
  fs.writeFileSync(path.join(outDir, 'coverage.json'), `${JSON.stringify(figure)}\n`)
}
