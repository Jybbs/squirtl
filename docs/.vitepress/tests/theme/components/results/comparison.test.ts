// @vitest-environment happy-dom
import { type VueWrapper, enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it }                          from 'vitest'
import { nextTick }                                                 from 'vue'

import * as browser from '../../../common/browser.ts'
import { held }     from '../../../common/results.ts'

const { ResultsComparison } = await import('../../../../theme/components/results/comparison.tsx')

enableAutoUnmount(afterEach)

/**
 * Reads the opacity of the curves, then of the last evaluation, the first two
 * parts of the figure as each side widens and folds.
 */
const sides = (wrapper: VueWrapper) => wrapper.findAll('svg > g[opacity]')
  .slice(0, 2)
  .map(part => part.attributes('opacity'))

/**
 * Mounts the comparison in a box `width` pixels wide, 688 unless given,
 * under the motion `preference` sets, reduced unless given, where each side
 * widens and folds at once.
 */
async function mounted(
  width      : number                          = 688,
  preference : typeof browser.preference.value = 'reduce'
): Promise<VueWrapper> {
  held.runs                = true
  browser.preference.value = preference
  const resize             = browser.stubSize()
  const wrapper            = mount(ResultsComparison, { attachTo: document.body })
  await nextTick()
  resize(width, 300)
  await flushPromises()
  return wrapper
}

describe('ResultsComparison', () => {
  it('draws nothing until a run is committed', () => {
    held.runs = false
    expect(mount(ResultsComparison).html()).toBe('')
  })

  it('draws a lane a group, reading each lane’s verdict as its interval of the odds against random presses '
   + 'falls', async () => {
    const wrapper = await mounted()
    const side    = wrapper.find('[aria-label^="Last evaluation"]')

    await side.trigger('focus')

    expect(wrapper.find('svg').text().match(/VS (?:RANDOM|BEDROOM)(?:BEATS|BELOW|NOT CLEAR|WORSE|BETTER)/gu))
      .toStrictEqual([
        'VS RANDOMBELOW', 'VS RANDOMBEATS', 'VS RANDOMBEATS', 'VS BEDROOMNOT CLEAR', 'VS RANDOMNOT CLEAR',
        'VS RANDOMNOT CLEAR', 'VS BEDROOMWORSE'
      ])
  })

  it('stands every seed’s row whole at once under reduced motion', async () => {
    const wrapper = await mounted()

    expect(wrapper.find('svg').findAll('clipPath rect').filter(rect => Number(rect.attributes('width')) <= 0))
      .toStrictEqual([])
  })

  it('draws a whisker for each verdict whose odds carry an interval', async () => {
    const wrapper = await mounted()
    await wrapper.find('[aria-label^="Last evaluation"]').trigger('focus')
    await flushPromises()

    expect(wrapper.find('svg').findAll('.results-whisker')).toHaveLength(5)
  })

})

describe('ResultsComparison’s fold', () => {
  it('widens the side holding focus and folds the other, returning both to rest on blur', async () => {
    const wrapper = await mounted()
    const curves  = wrapper.find('[aria-label^="Learning curves"]')
    const finals  = wrapper.find('[aria-label^="Last evaluation"]')
    const read    = async () => {
      await flushPromises()
      return [sides(wrapper), wrapper.find('svg').text().includes('VS RANDOM')]
    }

    const rest = await read()
    await finals.trigger('focus')
    const opened = await read()
    await finals.trigger('blur')
    await curves.trigger('focus')
    const folded = await read()

    expect([rest, opened, folded]).toStrictEqual([
      [['1', '1'], false],
      [['0', '1'], true],
      [['1', '0'], true]
    ])
  })

  it('widens the side a mouse rests on over the side holding focus, and focuses a side on a '
   + 'touch', async () => {
    const wrapper = await mounted()
    const curves  = wrapper.find<HTMLElement>('[aria-label^="Learning curves"]')
    const finals  = wrapper.find<HTMLElement>('[aria-label^="Last evaluation"]')

    await finals.trigger('pointerdown', { pointerType: 'touch' })
    await finals.trigger('focus')
    await curves.trigger('pointerenter', { pointerType: 'mouse' })
    await flushPromises()
    const hovered = sides(wrapper)
    await curves.trigger('pointerleave', { pointerType: 'mouse' })
    await flushPromises()

    expect([document.activeElement === finals.element, hovered, sides(wrapper)])
      .toStrictEqual([true, ['1', '0'], ['0', '1']])
  })

})

describe('ResultsComparison’s fold at rest', () => {
  it('leaves the sides at rest on a touch passing over them or a mouse pressing one', async () => {
    const wrapper = await mounted()
    const curves  = wrapper.find<HTMLElement>('[aria-label^="Learning curves"]')

    await curves.trigger('pointerenter', { pointerType: 'touch' })
    await curves.trigger('pointerdown', { pointerType: 'mouse' })
    await curves.trigger('pointerleave', { pointerType: 'touch' })
    await flushPromises()

    expect([document.activeElement === curves.element, sides(wrapper)]).toStrictEqual([false, ['1', '1']])
  })

  it('returns both sides to rest on blur, each side a tab stop', async () => {
    const wrapper = await mounted()
    const finals  = wrapper.find('[aria-label^="Last evaluation"]')

    await finals.trigger('focus')
    await finals.trigger('blur')
    await flushPromises()

    expect([wrapper.findAll('[role="group"]').map(side => side.attributes('tabindex')), sides(wrapper)])
      .toStrictEqual([['0', '0'], ['1', '1']])
  })

})

describe('ResultsComparison’s layout', () => {
  it('stacks the curves above the last evaluation in a narrow box, with no side to widen', async () => {
    const wrapper = await mounted(390, 'no-preference')

    expect([wrapper.findAll('[role="group"]').length, wrapper.find('svg').text().includes('VS BEDROOM')])
      .toStrictEqual([0, true])
  })

  it('decodes each mark under what it marks in the legend', async () => {
    const wrapper = await mounted()

    expect(wrapper.text()).toContain('Random presses')
    expect(wrapper.text()).toContain('10% [0, 25]')
  })
})
