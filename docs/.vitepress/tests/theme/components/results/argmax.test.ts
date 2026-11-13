// @vitest-environment happy-dom
import { type VueWrapper, enableAutoUnmount, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi }        from 'vitest'
import { nextTick }                                   from 'vue'

import * as pointer from '../../../common/pointer.ts'

/**
 * Whether the stand-in below holds the seven runs the fixture holds or no run
 * at all.
 */
const held = vi.hoisted(() => ({ runs: false }))

vi.mock('../../../../lib/results/results.ts', async original => {
  const module  = await original<typeof import('../../../../lib/results/results.ts')>()
  const fixture = await import('../../../lib/results/fixtures/results.json')
  const none    = { comparisons: [], random: null, runs: [] }
  const shown   = () => (held.runs ? fixture.default : none) as unknown as typeof module.COMMITTED
  return {
    ...module,
    get COMMITTED() { return shown() },
    groupsOf: (results = shown()) => module.groupsOf(results)
  }
})

const { ResultsArgmax } = await import('../../../../theme/components/results/argmax.tsx')

enableAutoUnmount(afterEach)

/**
 * Reads each seed's tile, its seed, its sampled count, and its mark, beside
 * whether it is marked as differing.
 */
const tiles = (wrapper: VueWrapper) =>
  wrapper.findAll('.results-seed').map(tile => [tile.text(), tile.attributes('data-differs') !== undefined])

/**
 * Reads the row of evaluations, each pick's text beside the row's columns and
 * its thumb's width.
 */
const picks = (wrapper: VueWrapper) => [
  wrapper.findAll('.results-pick').map(pick => pick.text()),
  wrapper.get<HTMLElement>('.results-pick').element.parentElement!.style.gridTemplateColumns,
  wrapper.get<HTMLElement>('[role="slider"]').element.style.width
]

describe('ResultsArgmax', () => {
  it('draws nothing until a PPO run is committed', () => {
    held.runs = false
    expect(mount(ResultsArgmax).html()).toBe('')
  })

  it('opens on the last evaluation under the takeaway, a column and a thumb width per evaluation', () => {
    held.runs     = true
    const wrapper = mount(ResultsArgmax)

    expect([
      wrapper.find('p').text(),
      pointer.sliderState(wrapper),
      tiles(wrapper),
      picks(wrapper)
    ]).toStrictEqual([
      'Sampling and the most likely press differ at 1 of PPO’s 12 evaluations, and at none from 1.00M steps on.',
      ['2', 'Evaluation 3 of 3, 1.50M steps, No seed differs, so nothing is marked'],
      [['Seed 230of 30', false], ['Seed 330of 30', false], ['Seed 430of 30', false], ['Seed 530of 30', false]],
      [['11', '2', '3'], 'repeat(3, minmax(0, 1fr))', `${100 / 3}%`]
    ])
  })

  it('marks each differing seed with its count at the most likely press once Home steps to the first', async () => {
    held.runs     = true
    const wrapper = mount(ResultsArgmax, { attachTo: document.body })
    const thumb   = wrapper.get('[role="slider"]')

    await thumb.trigger('focusin')
    await thumb.trigger('keydown', { key: 'Home' })
    await nextTick()

    expect([wrapper.findAll('[data-picked]').map(pick => pick.text()), tiles(wrapper)]).toStrictEqual([
      ['11'],
      [['Seed 215of 30Likeliest 0', true], ['Seed 38of 30', false], ['Seed 423of 30', false], ['Seed 530of 30', false]]
    ])
  })

  it('steps to the evaluation a press on the row lands on', async () => {
    held.runs     = true
    const wrapper = mount(ResultsArgmax, { attachTo: document.body })

    await pointer.press(pointer.controlOf(wrapper, 300), 150)
    await nextTick()

    expect(pointer.sliderState(wrapper)[0]).toBe('1')
  })
})
