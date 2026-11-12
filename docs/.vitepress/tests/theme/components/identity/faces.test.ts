// @vitest-environment happy-dom
import { enableAutoUnmount, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'

import * as faces   from '../../../../lib/identity/faces.ts'
import { IDENTITY } from '../../../../lib/identity/identity.ts'

const { IdentityFaces } = await import('../../../../theme/components/identity/faces.tsx')

enableAutoUnmount(afterEach)

/**
 * Reads the place of the copy each face's stack shows.
 */
const shownCopies = (wrapper: ReturnType<typeof mount>): number[] =>
  wrapper.findAll('.identity-stack').map(stack => stack.findAll('.identity-copy').findIndex(copy => copy.attributes('data-shown') === 'true'))

describe('IdentityFaces', () => {
  it('names each face in its role’s order beside what it sets, a swatch for each weight it loads', () => {
    const wrapper = mount(IdentityFaces)

    expect(wrapper.findAll('.identity-name').map(name => name.text()))
      .toStrictEqual(faces.ROLES.map(role => `${IDENTITY.faces[role].family}${IDENTITY.faces[role].purpose}`))
    expect(wrapper.findAll('[role="radiogroup"]').map(group => group.findAll('button').length))
      .toStrictEqual(faces.ROLES.map(role => faces.WEIGHTS[role].length))
    expect(wrapper.text()).toBePublishedProse()
  })

  it('opens every face at its lightest weight and holds a face loading one weight still', () => {
    const wrapper = mount(IdentityFaces)
    const lone    = faces.ROLES.map(role => faces.WEIGHTS[role].length === 1)

    expect(shownCopies(wrapper)).toStrictEqual(faces.ROLES.map(() => 0))
    expect(wrapper.findAll('[role="radiogroup"]').map(group => group.get('button').attributes('disabled') !== undefined)).toStrictEqual(lone)
  })

  it('shows the copy of every part a face sets at the weight a reader presses', async () => {
    const wrapper = mount(IdentityFaces, { attachTo: document.body })
    const body    = faces.ROLES.indexOf('body')

    await wrapper.findAll('[role="radiogroup"]')[body]!.findAll('button').at(-1)!.trigger('click')

    expect(shownCopies(wrapper)[body]).toBe(faces.WEIGHTS.body.length - 1)
  })

  it('sets the setting’s name in the body’s paragraph at the weight pressed for code', async () => {
    const wrapper = mount(IdentityFaces, { attachTo: document.body })
    const code    = faces.ROLES.indexOf('code')

    await wrapper.findAll('[role="radiogroup"]')[code]!.findAll('button')[1]!.trigger('click')

    expect(wrapper.findAll('.identity-inline').at(-1)!.findAll('code').map(each => each.attributes('data-shown')))
      .toStrictEqual(faces.WEIGHTS.code.map((_, n) => String(n === 1)))
  })
})
