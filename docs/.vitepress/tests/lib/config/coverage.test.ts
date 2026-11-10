import fs   from 'node:fs'
import path from 'node:path'

import { describe, expect } from 'vitest'

import { writeCoverage } from '../../../lib/config/coverage.ts'
import { test }          from '../../common/checkout.ts'

describe('writeCoverage', () => {
  test('writes the total the suite’s report holds into the built site', ({ checkout }) => {
    const report           = { files: {}, totals: { percent_covered: 97.1234, percent_covered_display: '97.12' } }
    const { metaUrl, root } = checkout({ '.cache/coverage/coverage.json': JSON.stringify(report) })
    const outDir           = path.join(root, 'dist')
    fs.mkdirSync(outDir)
    writeCoverage(outDir, metaUrl)

    expect(JSON.parse(fs.readFileSync(path.join(outDir, 'coverage.json'), 'utf8'))).toStrictEqual({ percent: '97.12' })
  })

  test('writes nothing where the suite has written no report', ({ checkout }) => {
    const { metaUrl, root } = checkout()
    writeCoverage(root, metaUrl)

    expect(fs.existsSync(path.join(root, 'coverage.json'))).toBe(false)
  })
})
