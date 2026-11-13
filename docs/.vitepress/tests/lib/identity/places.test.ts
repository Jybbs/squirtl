import { describe, expect, it } from 'vitest'

import * as places from '../../../lib/identity/places.ts'

describe('repositoryOf', () => {
  it.each([
    ['https://github.com/Jybbs/squirtl', { name: 'squirtl', owner: 'Jybbs' }],
    ['https://github.com/Jybbs/squirtl/', { name: 'squirtl', owner: 'Jybbs' }],
    ['https://github.com/', { name: '', owner: '' }]
  ])('reads %s as %o', (url, repository) => {
    expect(places.repositoryOf(url)).toStrictEqual(repository)
  })
})
