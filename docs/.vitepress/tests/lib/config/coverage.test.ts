import fs   from 'node:fs'
import path from 'node:path'

import { describe, expect } from 'vitest'

import { writeCoverage } from '../../../lib/config/coverage.ts'
import { test }          from '../../common/checkout.ts'

describe('writeCoverage', () => {
  test.for([
    [97.1234, '97'],
    [97.5, '98']
  ] as const)('writes the total %d the suite’s report holds as the whole percent %s', ([total, percent], { checkout }) => {
    const report            = { files: {}, totals: { percent_covered: total } }
    const { metaUrl, root } = checkout({ '.cache/coverage/coverage.json': JSON.stringify(report) })
    const outDir            = path.join(root, 'dist')
    fs.mkdirSync(outDir)
    writeCoverage(outDir, metaUrl)

    expect(JSON.parse(fs.readFileSync(path.join(outDir, 'coverage.json'), 'utf8'))).toStrictEqual({ percent })
  })

  test('writes nothing where the suite has written no report', ({ checkout }) => {
    const { metaUrl, root } = checkout()
    writeCoverage(root, metaUrl)

    expect(fs.existsSync(path.join(root, 'coverage.json'))).toBe(false)
  })
})
