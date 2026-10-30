// @vitest-environment happy-dom
import { enableAutoUnmount, mount }            from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { shallowRef }                          from 'vue'

import { stageKey } from '../../../../lib/front/hero.ts'

/**
 * The hero the front page's frontmatter declares in a case.
 */
const HERO = { name: 'SquiRtL', tagline: 'Trains an agent.', text: 'Learns the walk.' }

vi.mock('vitepress', () => ({ useData: () => ({ frontmatter: { value: { hero: HERO } } }) }))

const { HeroName } = await import('../../../../theme/components/front/hero.tsx')

enableAutoUnmount(afterEach)

describe('HeroName', () => {
  it('sets the name for a reader and as the glyphs the flight lands on, the R and L in link color', () => {
    const wrapper = mount(HeroName)
    const glyphs  = wrapper.findAll('[data-glyph]')
    const linked  = glyphs.filter(glyph => glyph.classes('text-link')).map(glyph => glyph.text())

    expect(wrapper.find('.visually-hidden').text()).toBe(HERO.name)
    expect(glyphs.map(glyph => glyph.text()).join('')).toBe(HERO.name)
    expect(linked).toStrictEqual(['R', 'L'])
  })

  it('sets the tagline in the heading and the byline beneath it, each a line that rises in', () => {
    const wrapper = mount(HeroName)

    expect(wrapper.findAll('[data-rise]').map(line => line.text())).toStrictEqual([HERO.text, HERO.tagline])
    expect(wrapper.find('h1').text()).toContain(HERO.text)
  })

  it('hands its copy to the stage while mounted', () => {
    const stage   = { copy: shallowRef<HTMLElement | null>(null) }
    const wrapper = mount(HeroName, { global: { provide: { [stageKey as symbol]: stage } } })
    const held    = stage.copy.value
    wrapper.unmount()

    expect([held?.querySelectorAll('[data-glyph]').length, stage.copy.value])
      .toStrictEqual([HERO.name.length, null])
  })
})
