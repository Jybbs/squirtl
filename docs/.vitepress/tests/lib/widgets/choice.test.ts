// @vitest-environment happy-dom
import { enableAutoUnmount, mount }        from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { defineComponent, h }              from 'vue'

import { useChoice } from '../../../lib/widgets/choice.ts'

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
