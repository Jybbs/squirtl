// @vitest-environment happy-dom
import { enableAutoUnmount, mount }        from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'

import { IDENTITY, contrast } from '../../../../lib/identity/identity.ts'
import * as palette           from '../../../../lib/identity/palette.ts'

const { IdentityPalette } = await import('../../../../theme/components/identity/palette.tsx')

enableAutoUnmount(afterEach)

/**
 * Reads the card's name, what it names, and its hex.
 */
const card = (wrapper: ReturnType<typeof mount>): string[] =>
  wrapper.get('.identity-card').findAll('.font-code').slice(0, 2).map(each => each.text())

/**
 * Finds the band of the color `token` names.
 */
const band = (wrapper: ReturnType<typeof mount>, token: string) =>
  wrapper.get(`[aria-label="${palette.NAMED.find(each => each.token === token)!.name}, ${palette.NAMED.find(each => each.token === token)!.hex}"]`)

describe('IdentityPalette', () => {
  it('opens on the first color, its ramp on both grounds, its card measuring it on each', () => {
    const wrapper = mount(IdentityPalette, { attachTo: document.body })
    const first   = palette.NAMED[0]!

    expect([
      wrapper.findAll('.identity-band').length,
      wrapper.findAll('.identity-ground').length,
      wrapper.findAll('.identity-step').length,
      card(wrapper),
      wrapper.findAll('.identity-verdict').length
    ]).toStrictEqual([palette.NAMED.length, 2, 10, [first.token, first.hex], 2])
    expect(wrapper.text()).toBePublishedProse()
  })

  it('names a color carrying no ramp as standing alone once a reader picks it', async () => {
    const wrapper = mount(IdentityPalette, { attachTo: document.body })

    await band(wrapper, 'ground').trigger('click')

    expect([wrapper.findAll('.identity-ground').length, wrapper.get('.identity-ramp').text()])
      .toStrictEqual([0, `${IDENTITY.neutrals.ground.name} carries no ramp, so it stands alone in both schemes.`])
  })

  it('shows the step a reader picks on its ground, clears it on a second press, and clears it on another color', async () => {
    const wrapper = mount(IdentityPalette, { attachTo: document.body })
    const step    = () => wrapper.findAll('.identity-step')[9]!

    await step().trigger('click')
    const picked = card(wrapper)
    await step().trigger('click')
    const cleared = card(wrapper)
    await step().trigger('click')
    await band(wrapper, 'primary').trigger('click')
    const first = palette.NAMED[0]!

    expect([picked, cleared, card(wrapper)]).toStrictEqual([
      [`on ${palette.GROUNDS.dark.name}`, palette.stepsOf(palette.hueOfToken(first.token)!, 'dark')[4]!.hex],
      [first.token, first.hex],
      ['primary', IDENTITY.colors.primary.hex]
    ])
  })

})

describe('IdentityPalette’s card', () => {
  it('reads each meter’s verdict from the color’s contrast on its ground', () => {
    const wrapper = mount(IdentityPalette)
    const hex     = palette.NAMED[0]!.hex

    expect(wrapper.findAll('.identity-verdict').map(each => each.attributes('data-level')))
      .toStrictEqual(palette.SCHEMES.map(scheme => palette.levelOf(contrast(hex, palette.GROUNDS[scheme].hex))))
  })
})
