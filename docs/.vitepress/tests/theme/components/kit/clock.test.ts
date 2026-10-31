// @vitest-environment happy-dom
import { enableAutoUnmount, mount }        from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { defineComponent, h }              from 'vue'

import { IDENTITY }      from '../../../../lib/identity/identity.ts'
import { drawClockChip } from '../../../../theme/components/kit/clock.tsx'

/**
 * The width of the rule on the chip's leading edge, the identity's bar.
 */
const RULE = IDENTITY.lengths.borders.bar

enableAutoUnmount(afterEach)

describe('drawClockChip', () => {
  it('sets the reading on a ground with a rule on its leading edge, centered past the rule', () => {
    const chip = mount(defineComponent({
      setup: () => () => h('svg', [drawClockChip(40, '12 steps', 104)])
    }))
    const [ground, rule] = chip.findAll('rect')

    expect(chip.get('g').attributes('transform')).toBe('translate(40 0)')
    expect([ground!.classes(), ground!.attributes('width'), rule!.attributes('width')])
      .toStrictEqual([['clock-chip'], '104', String(RULE)])
    expect([chip.get('text').text(), chip.get('text').attributes('x')])
      .toStrictEqual(['12 steps', String((104 + RULE) / 2)])
  })
})
