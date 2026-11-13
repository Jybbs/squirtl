// @vitest-environment happy-dom
import { enableAutoUnmount, mount }        from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { defineComponent, h, ref }         from 'vue'

import { useChoice, usePick, useSwitches } from '../../../lib/widgets/choice.ts'

enableAutoUnmount(afterEach)

/**
 * Mounts a group of `values` as options, recording each one chosen.
 */
function mounted(values: readonly string[]) {
  const chosen: string[] = []
  const wrapper          = mount(defineComponent({
    setup: () => {
      const choice = useChoice(values, value => { chosen.push(value) })
      return () => h('div', choice.root.value, values.map(value => h('button', choice.item(value), value)))
    }
  }), { attachTo: document.body })
  return { chosen, wrapper }
}

describe('useChoice', () => {
  it('presses the first option and the one a reader presses, never leaving none pressed', async () => {
    const { chosen, wrapper } = mounted(['one', 'two'])
    const checked             = () => wrapper.findAll('[role="radio"]').map(radio => radio.attributes('aria-checked'))
    const first               = checked()

    await wrapper.findAll('button')[1]!.trigger('click')
    const second = checked()
    await wrapper.findAll('button')[1]!.trigger('click')

    expect([first, second, checked(), chosen]).toStrictEqual([['true', 'false'], ['false', 'true'], ['false', 'true'], ['two']])
  })
})

describe('useChoice’s own ref', () => {
  it('presses the option the caller sets in the ref it hands, and writes a reader’s press back to it', async () => {
    const pressed = ref('two')
    const wrapper = mount(defineComponent({
      setup: () => {
        const choice = useChoice(['one', 'two'], () => {}, pressed)
        return () => h('div', choice.root.value, ['one', 'two'].map(value => h('button', choice.item(value), value)))
      }
    }), { attachTo: document.body })
    const checked = () => wrapper.findAll('[role="radio"]').map(radio => radio.attributes('aria-checked'))
    const first   = checked()

    await wrapper.findAll('button')[0]!.trigger('click')

    expect([first, checked(), pressed.value]).toStrictEqual([['false', 'true'], ['true', 'false'], 'one'])
  })
})

describe('usePick', () => {
  it('picks the option a reader presses and clears it on a second press', async () => {
    const picked  = ref<string | null>(null)
    const wrapper = mount(defineComponent({
      setup: () => {
        const pick = usePick(['one', 'two'], picked)
        return () => h('div', pick.root.value, ['one', 'two'].map(value => h('button', pick.item(value), value)))
      }
    }), { attachTo: document.body })
    const seen: (string | null)[] = []

    await wrapper.findAll('button')[1]!.trigger('click')
    seen.push(picked.value)
    await wrapper.findAll('button')[1]!.trigger('click')
    seen.push(picked.value)

    expect(seen).toStrictEqual(['two', null])
  })
})

describe('useSwitches', () => {
  it('presses any number at once in the order of the values, the ones the caller sets first', async () => {
    const pressed = ref<ReadonlySet<string>>(new Set(['two']))
    const wrapper = mount(defineComponent({
      setup: () => {
        const switches = useSwitches(['one', 'two', 'three'], pressed)
        return () => h('div', switches.root.value, ['one', 'two', 'three'].map(value => h('button', switches.item(value), value)))
      }
    }), { attachTo: document.body })
    const states = () => wrapper.findAll('button').map(button => button.attributes('data-state'))
    const first  = states()

    await wrapper.findAll('button')[2]!.trigger('click')
    await wrapper.findAll('button')[0]!.trigger('click')

    expect([first, states(), [...pressed.value]]).toStrictEqual([['off', 'on', 'off'], ['on', 'on', 'on'], ['one', 'two', 'three']])
  })
})
