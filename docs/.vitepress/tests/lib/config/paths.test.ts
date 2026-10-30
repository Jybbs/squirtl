import path from 'node:path'

import { describe, expect } from 'vitest'

import * as paths from '../../../lib/config/paths.ts'
import { test }   from '../../common/checkout.ts'

describe('paths', () => {
  test('finds each folder from the root of the checkout holding the caller', ({ checkout }) => {
    const { metaUrl, root } = checkout()

    expect([
      paths.repoRoot(metaUrl),
      paths.docsDir(metaUrl),
      paths.pagesDir(metaUrl),
      paths.publicDir(metaUrl),
      paths.cacheDir(metaUrl, 'vitest')
    ]).toStrictEqual([
      root,
      path.join(root, 'docs'),
      path.join(root, 'docs', 'pages'),
      path.join(root, 'docs', 'public'),
      path.join(root, '.cache', 'vitest')
    ])
  })

  test('fails where no folder above the caller holds a .git', () => {
    expect(() => paths.repoRoot('file:///squirtl-15-no-checkout/docs/config.ts')).toThrow('No checkout holds')
  })
})
