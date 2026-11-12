import { describe, expect, it } from 'vitest'

import * as faces   from '../../../lib/identity/faces.ts'
import { IDENTITY } from '../../../lib/identity/identity.ts'

describe('weightsOf', () => {
  it('reads each loaded weight, lightest first', () => {
    expect(faces.weightsOf('wght@700;400;500').map(each => each.label)).toStrictEqual(['400', '500', '700'])
  })

  it('reads a range of the weight axis as every hundred across it, the other axes passed over', () => {
    expect(faces.weightsOf('opsz,wght@7..72,400..600').map(each => each.weight)).toStrictEqual([400, 500, 600])
  })

  it('reads the italic once, at its lightest weight, after every upright weight', () => {
    expect(faces.weightsOf('ital,wght@0,400..500;1,500..700')).toStrictEqual([
      { italic: false, label: '400', weight: 400 },
      { italic: false, label: '500', weight: 500 },
      { italic: true, label: 'Italic', weight: 500 }
    ])
  })
})

describe('WEIGHTS', () => {
  it('reads each role’s weights from the axes its face loads', () => {
    expect(faces.WEIGHTS).toStrictEqual(Object.fromEntries(faces.ROLES.map(role => [role, faces.weightsOf(IDENTITY.faces[role].axes)])))
  })

  it('gives every face at least one weight', () => {
    expect(faces.ROLES.every(role => faces.WEIGHTS[role].length > 0)).toBe(true)
  })
})
