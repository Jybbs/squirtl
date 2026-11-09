// @vitest-environment happy-dom
import { enableAutoUnmount, mount }        from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { nextTick }                        from 'vue'

import * as pointer from '../../../common/pointer.ts'

const { MethodsDiscount } = await import('../../../../theme/components/methods/discount.tsx')

enableAutoUnmount(afterEach)

describe('MethodsDiscount', () => {
  it('opens on the setting, the starter of each episode counted under it', () => {
    const wrapper = mount(MethodsDiscount)

    expect([pointer.sliderState(wrapper), wrapper.findAllComponents({ name: 'Chip' }).map(chip => chip.text())]).toStrictEqual([
      ['94', 'Discount 0.997, half its weight at 231 steps'],
      ['The walk0.3688', 'A wander0.0000', 'The setting0.997']
    ])
  })

  it('moves the half point and the discount to the slider’s end on End', async () => {
    const wrapper = mount(MethodsDiscount, { attachTo: document.body })

    const thumb   = wrapper.get('[role="slider"]')

    await thumb.trigger('focusin')
    await thumb.trigger('keydown', { key: 'End' })
    await nextTick()

    expect(wrapper.findAllComponents({ name: 'Chip' }).at(-1)!.text()).toBe('Discount0.9998')
  })
})
