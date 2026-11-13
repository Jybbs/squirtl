import fs   from 'node:fs'
import path from 'node:path'

import { describe, expect } from 'vitest'

import { coverageOf, writeCoverage } from '../../../lib/config/coverage.ts'
import { test }                      from '../../common/checkout.ts'
import { FACTS }                     from '../../common/facts.ts'

describe('coverageOf', () => {
  test.for([
    [97.1234, '97'],
    [97.5, '98']
  ] as const)('reads the total %d the suite’s report holds as the whole percent %s', ([total, percent], { checkout }) => {
    const report      = { files: {}, totals: { percent_covered: total } }
    const { metaUrl } = checkout({ '.cache/coverage/coverage.json': JSON.stringify(report) })

    expect(coverageOf(metaUrl)).toBe(percent)
  })

  test('reads nothing where the suite has written no report', ({ checkout }) => {
    expect(coverageOf(checkout().metaUrl)).toBeUndefined()
  })
})

describe('writeCoverage', () => {
  test('writes the whole percent the report measured', ({ checkout }) => {
    const { root } = checkout()
    writeCoverage(root, '97')

    expect(JSON.parse(fs.readFileSync(path.join(root, 'coverage.json'), 'utf8'))).toStrictEqual({ percent: '97' })
  })

  test('writes nothing where no report measured a percent', ({ checkout }) => {
    const { root } = checkout()
    writeCoverage(root, FACTS.coverage)

    expect(fs.existsSync(path.join(root, 'coverage.json'))).toBe(false)
  })
})
