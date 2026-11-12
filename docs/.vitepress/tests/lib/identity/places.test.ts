import { describe, expect, it } from 'vitest'

import * as places from '../../../lib/identity/places.ts'
import { FACTS }   from '../../common/facts.ts'

describe('repositoryOf', () => {
  it.each([
    ['https://github.com/Jybbs/squirtl', { name: 'squirtl', owner: 'Jybbs' }],
    ['https://github.com/Jybbs/squirtl/', { name: 'squirtl', owner: 'Jybbs' }],
    ['https://github.com/', { name: '', owner: '' }]
  ])('reads %s as %o', (url, repository) => {
    expect(places.repositoryOf(url)).toStrictEqual(repository)
  })
})

describe('badgesOf', () => {
  it('reads the least Python, the coverage gate, and the host from the facts', () => {
    expect(places.badgesOf(FACTS)).toStrictEqual([
      { name: 'Python', value: `${FACTS.python}+` },
      { name: 'Coverage', value: `${FACTS.gate}%` },
      { name: 'Docs', value: FACTS.host }
    ])
  })
})
