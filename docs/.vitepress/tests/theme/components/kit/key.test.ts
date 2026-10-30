// @vitest-environment happy-dom
import { enableAutoUnmount, mount }        from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'

import type { KeyEntry } from '../../../../lib/widgets/chips.ts'
import { Chip }          from '../../../../theme/components/kit/chip.tsx'
import { Key }           from '../../../../theme/components/kit/key.tsx'

/**
 * The entries a case's key names, one in a hue and one in a role's.
 */
const ENTRIES: readonly KeyEntry[] = [
  { hue: 'fern', label: 'The first walk', name: 'First', value: '12' },
  { label: 'The second walk', name: 'Second', note: 'twice', role: 'starter' }
]

enableAutoUnmount(afterEach)

describe('Key as a strip', () => {
  it('sets each entry in one strip under the label as its mark, name, value, and unseen note', () => {
    const key   = mount(Key, { props: { entries: ENTRIES, label: 'The walks' } })
    const parts = key.findAll('ul > li').map(entry => entry.findAll(':scope > span').map(part => [
      part.attributes('aria-hidden'), part.text(), part.classes('visually-hidden')
    ]))

    expect(key.get('span').text()).toBe('The walks')
    expect(key.findAll('ul')).toHaveLength(1)
    expect(parts).toStrictEqual([
      [['true', '', false], [undefined, 'First', false], [undefined, '12', false]],
      [['true', '', false], [undefined, 'Second', false], [undefined, ', twice', true]]
    ])
    expect(key.findAllComponents(Chip)).toStrictEqual([])
  })

  it('inks each entry in its hue, or in its role’s, where it takes one', () => {
    const key   = mount(Key, { props: { entries: [...ENTRIES, { name: 'Third' }] } })
    const names = key.findAll('ul > li > span:nth-child(2)').map(name => name.classes().at(-1))

    expect(names).toStrictEqual(['text-fern-text', 'text-amethyst-text', 'text-ink'])
  })

  it('leaves out the label it is given none of, rings the entry lit in its hue, and dims the rest', () => {
    const key     = mount(Key, { props: { entries: ENTRIES, lit: 1 } })
    const entries = key.findAll('ul > li')

    expect(key.find(':scope > span').exists()).toBe(false)
    expect(entries.map(entry => [entry.classes('opacity-45'), entry.classes('border-amethyst-3')]))
      .toStrictEqual([[true, false], [false, true]])
  })

  it('dims no entry while none is lit', () => {
    const key = mount(Key, { props: { entries: ENTRIES } })

    expect(key.findAll('.opacity-45')).toStrictEqual([])
  })
})

describe('Key pressed and figured', () => {
  it('sets each entry as a button in a pressable key, reporting a resting mouse and a press', async () => {
    const key     = mount(Key, { props: { entries: ENTRIES, pressable: true, pressed: 0 } })
    const buttons = key.findAll('button')
    await buttons[1]!.trigger('pointerenter', { pointerType: 'mouse' })
    await buttons[1]!.trigger('pointerenter', { pointerType: 'touch' })
    await buttons[1]!.trigger('pointerleave')
    await buttons[0]!.trigger('click')

    expect(key.findAll('ul > li > button')).toHaveLength(2)
    expect(buttons.map(button => [button.attributes('aria-label'), button.attributes('aria-pressed')]))
      .toStrictEqual([['The first walk', 'true'], ['The second walk', 'false']])
    expect([key.emitted('hover'), key.emitted('press')]).toStrictEqual([[[1], [null]], [[0]]])
  })

  it('sets each entry’s two figures under the key’s heads, a chip beside them', () => {
    const entries = ENTRIES.map((entry, n) =>
      Object.assign({ figures: [`${n} of 2`, String(n * 10)] as const }, entry))
    const key   = mount(Key, { props: { entries, heads: ['Reached it', 'Steps'] } })
    const cells = key.findAll('.key-figures > span').map(cell => cell.text())

    expect(cells)
      .toStrictEqual(['', 'Reached it', 'Steps', 'First12', '0 of 2', '0', 'Secondtwice', '1 of 2', '10'])
    expect(key.findAllComponents(Chip).map(chip => chip.props('name'))).toStrictEqual(['First', 'Second'])
  })
})
