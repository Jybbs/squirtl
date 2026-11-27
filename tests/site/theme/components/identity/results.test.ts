// @vitest-environment happy-dom
import { mount }                from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import * as browser from '../../../common/browser.ts'

const { IdentityResults } = await import(
  '../../../../../docs/.vitepress/theme/components/identity/results.tsx'
)

describe('IdentityResults', () => {
  it('draws the comparison on made-up runs beside a card each for a run, a seed, and a share', async () => {
    const resize  = browser.stubSize()
    const wrapper = mount(IdentityResults, { attachTo: document.body })
    resize(688, 300)
    await wrapper.vm.$nextTick()
    const cards = wrapper.findAll('.identity-results-card')

    expect(cards.map(card => card.find('.identity-results-mark svg').exists()))
      .toStrictEqual([true, true, true])
    expect(cards.map(card => card.find('span:nth-child(2)').text()))
      .toStrictEqual(['A run', 'A seed', 'A share'])
    expect(wrapper.findAll('.results-legend')).toHaveLength(1)
    expect(wrapper.text()).toBePublishedProse()
  })
})
