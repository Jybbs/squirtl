// @vitest-environment happy-dom
import { mount }                from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import * as browser  from '../../../common/browser.ts'
import { held }      from '../../../common/results.ts'

const { EPISODES, MADE_UP } = await import('../../../../../docs/.vitepress/lib/results/made-up.ts')
const { percent }         = await import('../../../../../docs/.vitepress/lib/results/results.ts')
const { IdentityResults } = await import(
  '../../../../../docs/.vitepress/theme/components/identity/results.tsx'
)

const cells = (shades: number[]) => shades.map(shade => `results-cell-${shade}`)

describe('IdentityResults', () => {
  it('draws the comparison on made-up runs beside a card each for a run, a seed, and a share', async () => {
    held.runs     = false
    const resize  = browser.stubSize()
    const wrapper = mount(IdentityResults, { attachTo: document.body })
    resize(688, 300)
    await wrapper.vm.$nextTick()
    const cards = wrapper.findAll('.identity-results-card')

    expect(cards.map(card => card.findAll('.identity-results-mark [class^="results-cell-"]')
      .map(cell => cell.classes()[0])))
      .toStrictEqual([cells([0, 0, 1, 1, 2, 2, 3, 3]), [], cells([0, 1, 2, 3])])
    expect(cards[1]!.find('.identity-results-mark .fill-random').exists()).toBe(true)
    expect(cards[2]!.text()).toContain(`${EPISODES} episodes`)
    expect(cards.map(card => card.find('span:nth-child(2)').text()))
      .toStrictEqual(['A run', 'A seed', 'A share'])
    expect(wrapper.findAll('.results-legend')).toHaveLength(1)
    expect(wrapper.text()).toBePublishedProse()
  })

  it('draws a lane for each made-up comparison and none of the committed runs', async () => {
    held.runs     = false
    const resize  = browser.stubSize()
    const wrapper = mount(IdentityResults, { attachTo: document.body })
    resize(688, 300)
    await wrapper.vm.$nextTick()

    const lanes = wrapper.findComponent({ name: 'ResultsComparison' }).find('svg').text()

    expect(lanes.match(/\d+% \[\d+, \d+\]/gu))
      .toStrictEqual(MADE_UP.comparisons.map(comparison => percent(comparison.reached)))
  })
})
