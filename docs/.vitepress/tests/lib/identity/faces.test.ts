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

describe('glidesOf', () => {
  it.each([
    ['ital,opsz,wght@0,7..72,400..700;1,7..72,400..700', true],
    ['wght@400;500;700', false],
    ['CRSV,ELSH,wght@0,0,500', false]
  ])('reads whether %s loads the weight axis as a range', (axes, glides) => {
    expect(faces.glidesOf(axes)).toBe(glides)
  })
})

describe('copiesOf', () => {
  it('sets one upright copy of a gliding face at the weight picked beside its italic', () => {
    const heaviest = faces.WEIGHTS.body.findLastIndex(each => !each.italic)

    expect(faces.copiesOf('body', heaviest).map(({ shown, weight }) => [shown, weight.italic, weight.weight]))
      .toStrictEqual([[true, false, faces.WEIGHTS.body[heaviest]!.weight], [false, true, 400]])
  })

  it('shows a gliding face’s italic alone once the italic is picked', () => {
    expect(faces.copiesOf('body', faces.WEIGHTS.body.length - 1).map(copy => copy.shown)).toStrictEqual([false, true])
  })

  it('stacks a copy of any other face at each weight it loads, the one picked shown', () => {
    expect(faces.copiesOf('code', 1)).toStrictEqual(faces.WEIGHTS.code.map((weight, n) => ({ shown: n === 1, weight })))
  })
})
