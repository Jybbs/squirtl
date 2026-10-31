// @vitest-environment happy-dom
import { enableAutoUnmount, mount }            from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref }             from 'vue'

import { stageKey } from '../../lib/front/hero.ts'

vi.mock('vitepress/theme-without-fonts', () => ({
  default: {
    Layout: defineComponent({
      name  : 'DefaultLayout',
      setup : (_, { slots }) => () => h('div', Object.keys(slots).toSorted().map(name =>
        h('section', { 'data-slot': name }, slots[name]!())))
    })
  }
}))

vi.mock('vitepress', () => ({
  useData: () => ({
    frontmatter : { value: { hero: { name: 'SquiRtL', tagline: 'Plays.', text: 'Learns.' } } },
    isDark      : ref(false),
    page        : { value: { isNotFound: false, relativePath: 'index.md' } },
    theme       : { value: { edition: { host: 'squirtl.fyi', version: '0.1.0' } } }
  }),
  useRoute : () => ({ path: '/methods/agnet/' }),
  withBase : (path: string) => path
}))

const { Layout } = await import('../../theme/layout.ts')

enableAutoUnmount(afterEach)

describe('Layout', () => {
  it('fills the hero and the space before it, the space above a page’s title, and a missing address', () => {
    const slots = mount(Layout).findAll('[data-slot]').map(slot => slot.attributes('data-slot'))

    expect(slots)
      .toStrictEqual(['doc-before', 'home-hero-before', 'home-hero-image', 'home-hero-info', 'not-found'])
  })

  it('shares the stage the name’s copy registers on with the mark that flies onto it', () => {
    const wrapper = mount(Layout)
    const name    = wrapper.findComponent({ name: 'HeroName' })

    expect(name.vm.$.provides[stageKey as symbol].copy.value).toBe(name.element)
  })
})
