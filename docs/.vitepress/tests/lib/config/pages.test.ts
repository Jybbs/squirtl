import { describe, expect, it } from 'vitest'

import { withFrontPage } from '../../../lib/config/pages.ts'
import { IDENTITY }      from '../../../lib/identity/identity.ts'
import { FACTS }         from '../../common/facts.ts'

describe('withFrontPage', () => {
  it('gives the front page the home layout and a hero naming the project above its tagline', () => {
    expect(withFrontPage({ frontmatter: { kept: true }, relativePath: 'index.md' }, FACTS)).toStrictEqual({
      frontmatter: {
        hero: {
          actions : [{ link: FACTS.repository, text: 'The Code on GitHub' }],
          name    : IDENTITY.name,
          tagline : FACTS.description,
          text    : IDENTITY.tagline
        },
        kept   : true,
        layout : 'home'
      }
    })
  })

  it('leaves every other page as it was written', () => {
    expect(withFrontPage({ frontmatter: {}, relativePath: 'methods/index.md' }, FACTS)).toBeUndefined()
  })
})
