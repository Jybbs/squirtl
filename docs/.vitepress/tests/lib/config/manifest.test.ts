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
  'description = "Plays."',
  'version     = "0.2.0"',
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

  test.for([
    ['Homepage   = "https://squirtl.fyi/"', '', 'pyproject.toml declares no project.urls.Homepage'],
    [
      'Repository = "https://github.com/Jybbs/squirtl"',
      '',
      'pyproject.toml declares no project.urls.Repository'
    ],
    ['description = "Plays."', 'description = ""', 'pyproject.toml declares no project.description'],
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
