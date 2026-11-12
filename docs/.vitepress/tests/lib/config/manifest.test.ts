import { describe, expect } from 'vitest'

import { projectFacts } from '../../../lib/config/manifest.ts'
import { test }         from '../../common/checkout.ts'
import { FACTS }        from '../../common/facts.ts'

/**
 * A manifest declaring every key the site reads, at the values a case rewrites
 * one at a time.
 */
const MANIFEST = [
  '[project]',
  'description     = "Plays."',
  'keywords        = ["pokemon", "pyboy"]',
  'requires-python = ">=3.15"',
  'version         = "0.2.0"',
  '',
  '[project.urls]',
  'Homepage   = "https://squirtl.fyi/"',
  'Repository = "https://github.com/Jybbs/squirtl"',
  '',
  '[tool.coverage.report]',
  'fail_under = 95'
].join('\n')

describe('projectFacts', () => {
  test('reads the base path and the host from the homepage beside the declared facts', ({ checkout }) => {
    expect(projectFacts(checkout({ 'pyproject.toml': MANIFEST }).metaUrl)).toStrictEqual(FACTS)
  })

  test('reads the coverage the suite’s last report measured beside the declared facts', ({ checkout }) => {
    const report = JSON.stringify({ files: {}, totals: { percent_covered: 99.6 } })
    const { metaUrl } = checkout({ '.cache/coverage/coverage.json': report, 'pyproject.toml': MANIFEST })

    expect(projectFacts(metaUrl)).toStrictEqual({ ...FACTS, coverage: '100' })
  })

  test('serves under the path and at the host a homepage below the root of its host names', ({ checkout }) => {
    const manifest = MANIFEST.replace('"https://squirtl.fyi/"', '"https://example.org/squirtl/"')

    expect(projectFacts(checkout({ 'pyproject.toml': manifest }).metaUrl))
      .toMatchObject({ base: '/squirtl/', homepage: 'https://example.org/squirtl/', host: 'example.org' })
  })

  test.for([
    ['Homepage   = "https://squirtl.fyi/"', '', 'pyproject.toml declares no project.urls.Homepage'],
    [
      'Repository = "https://github.com/Jybbs/squirtl"',
      '',
      'pyproject.toml declares no project.urls.Repository'
    ],
    ['description     = "Plays."', 'description     = ""', 'pyproject.toml declares no project.description'],
    ['keywords        = ["pokemon", "pyboy"]', 'keywords        = []', 'pyproject.toml declares no project.keywords'],
    ['"pyboy"]', '7]', 'pyproject.toml declares no project.keywords'],
    ['requires-python = ">=3.15"', '', 'pyproject.toml declares no project.requires-python'],
    ['fail_under = 95', 'fail_under = "95"', 'pyproject.toml declares no tool.coverage.report.fail_under'],
    [
      '"https://squirtl.fyi/"',
      '"https://squirtl.fyi"',
      'pyproject.toml declares a project.urls.Homepage with no closing slash'
    ]
  ] as const)('fails by name where %s is %s', ([from, to, message], { checkout }) => {
    const { metaUrl } = checkout({ 'pyproject.toml': MANIFEST.replace(from, to) })

    expect(() => projectFacts(metaUrl)).toThrow(message)
  })
})
