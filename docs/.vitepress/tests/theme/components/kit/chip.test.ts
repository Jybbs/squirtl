// @vitest-environment happy-dom
import { enableAutoUnmount, mount }        from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'

import { Chip } from '../../../../theme/components/kit/chip.tsx'

enableAutoUnmount(afterEach)

describe('Chip', () => {
  it.each([
    ['agent', 'bg-denim-1', 'text-denim-text'],
    ['milestone', 'bg-heath-1', 'text-heath-text'],
    ['novelty', 'bg-fern-1', 'text-fern-text'],
    ['random', 'bg-seacaller-1', 'text-seacaller-text'],
    ['starter', 'bg-amethyst-1', 'text-amethyst-text'],
    ['none', 'chip-none', 'text-ink']
  ] as const)('tints a chip naming %s in its hue', (role, ground, name) => {
    const chip = mount(Chip, { props: { name: 'Steps', role } })

    expect(chip.classes()).toContain(ground)
    expect(chip.get('.tracking-caps').classes()).toContain(name)
  })

  it('tints a chip in the hue it names over the role it takes', () => {
    const chip = mount(Chip, { props: { hue: 'indigo', name: 'Methods', role: 'agent' } })

    expect(chip.classes()).toStrictEqual(expect.arrayContaining(['bg-indigo-1', 'border-indigo-mark']))
  })

  it('sets a swatch where it carries no mark, and leaves out a note and a value it is given none of', () => {
    const chip = mount(Chip, { props: { name: 'Steps', role: 'agent' } })

    expect(chip.find('.size-swatch').exists()).toBe(true)
    expect(chip.text()).toBe('Steps')
  })

  it('sets the game mark it is given in a round tile, then its name, note, and value', () => {
    const props = { name: 'Starter', note: 'once', role: 'starter', value: '+0.6' } as const
    const chip  = mount(Chip, { props: { ...props, mark: '<svg viewBox="0 0 16 16"></svg>' } })

    expect(chip.find('.chip-mark svg').exists()).toBe(true)
    expect(chip.findAll('span').slice(2).map(span => span.text())).toStrictEqual(['Starter', 'once', '+0.6'])
  })
})
