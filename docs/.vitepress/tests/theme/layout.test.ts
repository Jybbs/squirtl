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
    page        : { value: { isNotFound: false, relativePath: 'index.md' } }
  })
}))

const { Layout } = await import('../../theme/layout.ts')

enableAutoUnmount(afterEach)

describe('Layout', () => {
  it('fills the hero and the space before it on the front page, and the space above a page’s title', () => {
    const slots = mount(Layout).findAll('[data-slot]').map(slot => slot.attributes('data-slot'))

    expect(slots).toStrictEqual(['doc-before', 'home-hero-before', 'home-hero-image', 'home-hero-info'])
  })

  it('shares the stage the name’s copy registers on with the mark that flies onto it', () => {
    const wrapper = mount(Layout)
    const name    = wrapper.findComponent({ name: 'HeroName' })

    expect(name.vm.$.provides[stageKey as symbol].copy.value).toBe(name.element)
  })
})
