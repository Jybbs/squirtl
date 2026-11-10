// @vitest-environment happy-dom
import { type VueWrapper, enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi }                      from 'vitest'
import { nextTick }                                                 from 'vue'

import * as browser from '../../../common/browser.ts'

/**
 * Whether the stand-in below holds the committed runs, which hold none, or the
 * seven runs the fixture holds.
 */
const held = vi.hoisted(() => ({ runs: false }))

vi.mock('../../../../lib/results/results.ts', async original => {
  const module  = await original<typeof import('../../../../lib/results/results.ts')>()
  const fixture = await import('../../../lib/results/fixtures/results.json')
  const shown   = () => held.runs ? fixture.default as unknown as typeof module.COMMITTED : module.COMMITTED
  return {
    ...module,
    get COMMITTED() { return shown() },
    groupsOf: (results = shown()) => module.groupsOf(results)
  }
})

const { ResultsComparison } = await import('../../../../theme/components/results/comparison.tsx')
const { ResultsCurves }     = await import('../../../../theme/components/results/curves.tsx')

enableAutoUnmount(afterEach)

/**
 * Reads each toggle's name and whether it is pressed.
 */
const toggles = (wrapper: VueWrapper) =>
  wrapper.findAll('button').map(button => [button.find('span:nth-child(2)').text(), button.attributes('aria-pressed')])

/**
 * Reads how far each group's curve has traced out, as the width its clip
 * opens across.
 */
const traces = (wrapper: VueWrapper) => wrapper.findAll('clipPath rect').map(rect => Number(rect.attributes('width')))

/**
 * Reads the opacity of each part of the figure each side holds, the curves,
 * then the last evaluation, then the verdicts and the tabs that open as they
 * widen and fold.
 */
const sides = (wrapper: VueWrapper) => wrapper.findAll('svg > g[opacity]').map(part => part.attributes('opacity'))

describe.each([ResultsComparison, ResultsCurves])('$name', widget => {
  it('draws nothing until a run is committed', () => {
    held.runs = false
    expect(mount(widget).html()).toBe('')
  })
})

describe('ResultsCurves', () => {
  it('presses both PQN groups at first, the rest released, and toggles any group on a press', async () => {
    held.runs     = true
    const wrapper = mount(ResultsCurves)

    expect(toggles(wrapper)).toStrictEqual([
      ['Deep Q-network', 'false'], ['PPO', 'false'], ['PPO, curriculum', 'false'], ['PQN', 'true'], ['PQN, curriculum', 'true']
    ])

    await wrapper.findAll('button')[1]!.trigger('click')
    await wrapper.findAll('button')[3]!.trigger('click')

    expect(toggles(wrapper).map(([, pressed]) => pressed)).toStrictEqual(['false', 'true', 'false', 'false', 'true'])
    expect(wrapper.text()).toBePublishedProse()
  })

  it('moves focus along the toggles on the arrow keys, to either end on Home and End, and wraps past the last', async () => {
    held.runs     = true
    const wrapper = mount(ResultsCurves, { attachTo: document.body })
    const buttons = wrapper.findAll<HTMLButtonElement>('button')
    const focused = () => buttons.findIndex(button => button.element === document.activeElement)
    const press   = async (key: string) => {
      await wrapper.find<HTMLButtonElement>('button:focus').trigger('keydown', { key })
      await flushPromises()
      return focused()
    }

    buttons[0]!.element.focus()
    await buttons[0]!.trigger('focus')

    expect([await press('ArrowRight'), await press('ArrowRight'), await press('End'), await press('ArrowRight'), await press('ArrowLeft'), await press('Home')])
      .toStrictEqual([1, 2, 4, 0, 4, 0])
  })

})

describe('ResultsCurves’s traces', () => {
  it('stands every pressed curve whole at once under reduced motion, and none released', async () => {
    held.runs                = true
    browser.preference.value = 'reduce'
    const wrapper            = mount(ResultsCurves)

    await nextTick()

    expect(traces(wrapper).map(width => width > 100)).toStrictEqual([false, false, false, true, true])
  })

  it('traces a curve pressed under reduced motion out whole at once', async () => {
    held.runs                = true
    browser.preference.value = 'reduce'
    const wrapper            = mount(ResultsCurves)

    await nextTick()
    await wrapper.findAll('button')[1]!.trigger('click')
    await nextTick()

    expect(traces(wrapper).map(width => width > 100)).toStrictEqual([false, true, false, true, true])
  })

  it('holds every curve back until the plot first comes into view', async () => {
    held.runs = true
    // Fakes `Date` beside the timers, since `useTransition` times each frame through `Date.now`.
    vi.useFakeTimers({ toFake: ['Date', 'setTimeout', 'clearTimeout', 'requestAnimationFrame', 'cancelAnimationFrame'] })
    const sight   = browser.stubSight()
    const wrapper = mount(ResultsCurves, { attachTo: document.body })

    await vi.advanceTimersByTimeAsync(2000)
    const before = traces(wrapper)
    sight.show(true)
    await vi.advanceTimersByTimeAsync(2000)

    expect([before.map(width => width > 100), traces(wrapper).map(width => width > 100)]).toStrictEqual([
      [false, false, false, false, false], [false, false, false, true, true]
    ])
  })

})

describe('ResultsCurves’s releases', () => {
  it('draws a released curve back and traces a newly pressed one out at once, waiting on no earlier press', async () => {
    held.runs = true
    vi.useFakeTimers({ toFake: ['Date', 'setTimeout', 'clearTimeout', 'requestAnimationFrame', 'cancelAnimationFrame'] })
    const sight   = browser.stubSight()
    const wrapper = mount(ResultsCurves, { attachTo: document.body })

    await vi.advanceTimersByTimeAsync(0)
    sight.show(true)
    await vi.advanceTimersByTimeAsync(2000)
    await wrapper.findAll('button')[3]!.trigger('click')
    await wrapper.findAll('button')[0]!.trigger('click')
    await vi.advanceTimersByTimeAsync(700)

    expect(traces(wrapper).map(width => width > 100)).toStrictEqual([true, false, false, false, true])
  })
})

describe('ResultsCurves’s figures', () => {
  it('lists each group’s figures in a fixed slot under the plot, random presses last', () => {
    held.runs     = true
    const wrapper = mount(ResultsCurves)

    expect(wrapper.text()).toMatch(/Random pressesReached it0\.10 \[0\.00, 0\.25\] over 7$/u)
  })
})

/**
 * Mounts the comparison in a box 688 pixels wide under reduced motion, so
 * each side widens and folds at once.
 */
async function mounted(): Promise<VueWrapper> {
  held.runs                = true
  browser.preference.value = 'reduce'
  const resize             = browser.stubSize()
  const wrapper            = mount(ResultsComparison, { attachTo: document.body })
  await nextTick()
  resize(688, 300)
  await flushPromises()
  return wrapper
}

describe('ResultsComparison', () => {
  it('draws a lane a group, reading each lane’s verdict as its interval of the odds against random presses falls', async () => {
    const wrapper = await mounted()
    const side    = wrapper.find('[aria-label^="Last evaluation"]')

    await side.trigger('focus')

    expect(wrapper.find('svg').text().match(/VS (?:RANDOM|BEDROOM)(?:BEATS|BELOW|NOT CLEAR|WORSE|BETTER)/gu)).toStrictEqual([
      'VS RANDOMBELOW', 'VS RANDOMBEATS', 'VS RANDOMBEATS', 'VS BEDROOMNOT CLEAR', 'VS RANDOMNOT CLEAR', 'VS RANDOMNOT CLEAR', 'VS BEDROOMWORSE'
    ])
  })

  it('stands every seed’s row whole at once under reduced motion', async () => {
    const wrapper = await mounted()

    expect(wrapper.find('svg').findAll('clipPath rect').every(rect => Number(rect.attributes('width')) > 0)).toBe(true)
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
      return [sides(wrapper).slice(0, 2), wrapper.find('svg').text().includes('VS RANDOM')]
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

  it('widens the side a mouse rests on over the side holding focus, and focuses a side on a touch', async () => {
    const wrapper = await mounted()
    const curves  = wrapper.find<HTMLElement>('[aria-label^="Learning curves"]')
    const finals  = wrapper.find<HTMLElement>('[aria-label^="Last evaluation"]')

    await finals.trigger('pointerdown', { pointerType: 'touch' })
    await finals.trigger('focus')
    await curves.trigger('pointerenter', { pointerType: 'mouse' })
    await flushPromises()
    const hovered = sides(wrapper).slice(0, 2)
    await curves.trigger('pointerleave', { pointerType: 'mouse' })
    await flushPromises()

    expect([document.activeElement === finals.element, hovered, sides(wrapper).slice(0, 2)]).toStrictEqual([true, ['1', '0'], ['0', '1']])
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

    expect([document.activeElement === curves.element, sides(wrapper).slice(0, 2)]).toStrictEqual([false, ['1', '1']])
  })

  it('returns both sides to rest on blur, each side a tab stop', async () => {
    const wrapper = await mounted()
    const finals  = wrapper.find('[aria-label^="Last evaluation"]')

    await finals.trigger('focus')
    await finals.trigger('blur')
    await flushPromises()

    expect([wrapper.findAll('[role="group"]').map(side => side.attributes('tabindex')), sides(wrapper).slice(0, 2)])
      .toStrictEqual([['0', '0'], ['1', '1']])
  })

})

describe('ResultsComparison’s layout', () => {
  it('stacks the curves above the last evaluation in a narrow box, with no side to widen', async () => {
    held.runs     = true
    const resize  = browser.stubSize()
    const wrapper = mount(ResultsComparison, { attachTo: document.body })
    await nextTick()
    resize(390, 300)
    await flushPromises()

    expect([wrapper.findAll('[role="group"]').length, wrapper.find('svg').text().includes('VS BEDROOM')]).toStrictEqual([0, true])
  })

  it('decodes each mark under what it marks in the legend', async () => {
    const wrapper = await mounted()

    expect(wrapper.text()).toContain('Random presses')
    expect(wrapper.text()).toContain('10% [0, 25]')
  })
})
