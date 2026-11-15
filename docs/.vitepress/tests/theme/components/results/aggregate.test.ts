// @vitest-environment happy-dom
import { type VueWrapper, enableAutoUnmount, mount }                        from '@vue/test-utils'
import { type MockInstance, afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick }                                                           from 'vue'

import * as browser from '../../../common/browser.ts'

/**
 * Whether the stand-in below holds the runs the repository commits, five per
 * group under seeds 1 to 5, or no run at all.
 */
const held = vi.hoisted(() => ({ runs: true }))

vi.mock('../../../../lib/results/results.ts', async original => {
  const module = await original<typeof import('../../../../lib/results/results.ts')>()
  const none   = { comparisons: [], random: null, runs: [] }
  const shown  = () => (held.runs ? module.COMMITTED : none) as typeof module.COMMITTED
  return {
    ...module,
    get COMMITTED() { return shown() },
    groupsOf: (results = shown()) => module.groupsOf(results)
  }
})

const { ResultsAggregate } = await import('../../../../theme/components/results/aggregate.tsx')

enableAutoUnmount(afterEach)

/**
 * A widget mounted into the document, the call sizing its plot, and the spy
 * standing in for every animation an element plays.
 */
interface Mounted {
  played  : MockInstance<Element['animate']>
  wrapper : VueWrapper
}

/**
 * Reads the buttons over each column.
 */
const columnsOf = (wrapper: VueWrapper) => wrapper.findAll('ul[aria-label="Runs by group"] button')

/**
 * Mounts the widget with its plot `width` pixels wide, every animation an
 * element plays recorded rather than played.
 */
async function mounted(width = 688): Promise<Mounted> {
  const animation = { cancel: () => {} } as unknown as Animation
  const played    = vi.spyOn(Element.prototype, 'animate').mockReturnValue(animation)
  const resize    = browser.stubSize()
  const wrapper   = mount(ResultsAggregate, { attachTo: document.body })
  await nextTick()
  resize(width, 240)
  await nextTick()
  return { played, wrapper }
}

/**
 * Reads each run's group in the drawing, the one a press switches its seed
 * from.
 */
const runGroupsOf = (wrapper: VueWrapper) =>
  wrapper.findAll('svg g').filter(group => group.attributes('style')?.includes('transition-delay'))

/**
 * Reads every switch of a seed.
 */
const switchesOf = (wrapper: VueWrapper) => wrapper.findAll('ul[aria-label="Seeds kept"] button')

/**
 * Reads every line of text the drawing sets.
 */
const textsOf = (wrapper: VueWrapper) => wrapper.findAll('svg text').map(text => text.text())

beforeEach(() => {
  held.runs                = true
  browser.preference.value = 'reduce'
})

describe('ResultsAggregate', () => {
  it('draws nothing until a run is committed', async () => {
    held.runs = false
    expect((await mounted()).wrapper.html()).toBe('')
  })

  it('draws each group’s name, start, and share, and random presses’ figures', async () => {
    const { wrapper } = await mounted()
    const note        = new RegExp(
        "^Each interval as the runs report it, from SciPy's 9,999 draws over all five seeds\\. "
      + "Drawn again here, random presses' runs from \\d+% to \\d+%, within [0-2] points of it\\.$",
      'u'
    )
    expect([textsOf(wrapper).slice(3, 9), wrapper.get('p.text-small').text()]).toStrictEqual([
      ['Random presses 21% [14, 31]', 'DQN', 'Bedroom', '0%', '[0, 0]', 'PPO'],
      expect.stringMatching(note)
    ])
  })

  it.each([
    [688, 0],
    [300, 10]
  ])('sets each column’s interval at %d wide on %d lines of its own', async (width, lines) => {
    expect((await mounted(width)).wrapper.findAll('svg tspan')).toHaveLength(lines)
  })

  it('names each column to a screen reader with its figures', async () => {
    const { wrapper } = await mounted()
    expect(wrapper.get('[role="img"]').attributes('aria-label')).toMatch(
      /^Deep Q-network \(DQN\), from the bedroom: interquartile mean 0%, 95% interval 0 to 0% over 5 runs, /u
    )
  })

})

describe('ResultsAggregate’s seeds', () => {
  it('draws every figure again from the seeds a reader keeps, and names how', async () => {
    const { wrapper } = await mounted()
    await switchesOf(wrapper)[3]!.trigger('click')
    expect([
      wrapper.get('span').text(),
      textsOf(wrapper)[3],
      wrapper.get('p.text-small').text(),
      runGroupsOf(wrapper).filter(run => run.find('.fill-quiet').exists()).length
    ]).toStrictEqual([
      'Seeds kept, 4 runs each',
      'Random presses 18% [13, 27]',
        'Each interval drawn here from 9,999 draws over the 4 seeds kept, '
      + 'near what SciPy would report for them rather than on it.',
      5
    ])
  })

  it('keeps the last seed a reader would leave out', async () => {
    const { wrapper } = await mounted()
    const [one, two, three, four, five] = switchesOf(wrapper)
    await one!.trigger('click')
    await two!.trigger('click')
    await three!.trigger('click')
    await four!.trigger('click')
    await five!.trigger('click')
    expect([wrapper.get('span').text(), textsOf(wrapper)[3]])
      .toStrictEqual(['Seeds kept, 1 run each', 'Random presses 20%'])
  })

  it('leaves a seed out from a press on its run in a column, and keeps it again from a second', async () => {
    const { wrapper } = await mounted()
    const pressed     = () => switchesOf(wrapper).map(each => each.attributes('aria-pressed'))
    await runGroupsOf(wrapper)[0]!.trigger('click')
    const once = pressed()
    await runGroupsOf(wrapper)[0]!.trigger('click')
    expect([once, pressed()]).toStrictEqual([
      ['false', 'true', 'true', 'true', 'true'],
      ['true', 'true', 'true', 'true', 'true']
    ])
  })

})

describe('ResultsAggregate’s columns', () => {
  it('opens a column a reader presses, naming its runs, and shuts it on a second press', async () => {
    const { wrapper } = await mounted()
    const spoken      = () => wrapper.get('p.sr-only').text()
    await columnsOf(wrapper)[1]!.trigger('click')
    const opened = spoken()
    await columnsOf(wrapper)[1]!.trigger('click')
    expect([opened, spoken()])
      .toStrictEqual(['PPO, 5 runs: seed 1 100%; seed 2 100%; seed 3 100%; seed 4 100%; seed 5 100%', ''])
  })

  it('names a run whose seed is left out as such', async () => {
    const { wrapper } = await mounted()
    await switchesOf(wrapper)[0]!.trigger('click')
    await columnsOf(wrapper)[4]!.trigger('click')
    expect(wrapper.get('p.sr-only').text())
      .toBe('PQN along the curriculum, 5 runs: seed 1 0%, left out; '
          + 'seed 2 0%; seed 3 0%; seed 4 0%; seed 5 0%')
  })

  it.each([
    ['a mouse resting on a column', 'mouse', 300, 'pointer-events-auto'],
    ['a mouse passing across', 'mouse', 100, 'opacity-0'],
    ['a touch', 'touch', 300, 'opacity-0']
  ])('opens a column’s runs after %s: %s', async (_, pointerType, rest, shown) => {
    vi.useFakeTimers()
    const { wrapper } = await mounted()
    const plot        = wrapper.get('.h-race-plot')
    vi.spyOn(plot.element, 'getBoundingClientRect').mockReturnValue({ left: 0, width: 688 } as DOMRect)
    await plot.trigger('pointermove', { clientX: 200, pointerType })
    vi.advanceTimersByTime(rest)
    await nextTick()
    expect(runGroupsOf(wrapper)[5]!.classes()).toContain(shown)
  })

  it('shuts the runs a mouse opened once it leaves the plot', async () => {
    vi.useFakeTimers()
    const { wrapper } = await mounted()
    const plot        = wrapper.get('.h-race-plot')
    vi.spyOn(plot.element, 'getBoundingClientRect').mockReturnValue({ left: 0, width: 688 } as DOMRect)
    await plot.trigger('pointermove', { clientX: 20, pointerType: 'mouse' })
    await plot.trigger('pointermove', { clientX: 200, pointerType: 'mouse' })
    vi.advanceTimersByTime(300)
    await plot.trigger('pointerleave')
    vi.advanceTimersByTime(300)
    await nextTick()
    expect(runGroupsOf(wrapper)[5]!.classes()).toContain('opacity-0')
  })
})

describe('ResultsAggregate’s motion', () => {
  beforeEach(() => {
    browser.preference.value = 'no-preference'
  })

  it('settles the band, pops the switched runs, shakes the switch, and rocks no ball that held', async () => {
    const { played, wrapper } = await mounted()
    played.mockClear()
    await switchesOf(wrapper)[3]!.trigger('click')
    await nextTick()
    expect(Map.groupBy(played.mock.contexts, each => (each as Element).tagName)).toStrictEqual(new Map([
      ['BUTTON', [expect.anything()]],
      ['g', Array.from({ length: 6 }, () => expect.anything())]
    ]))
  })

  it('hops a switch as its seed is kept again, as its run fills', async () => {
    const { played, wrapper } = await mounted()
    await switchesOf(wrapper)[3]!.trigger('click')
    played.mockClear()
    await switchesOf(wrapper)[3]!.trigger('click')
    await nextTick()
    const hop = played.mock.calls.find((_, n) => (played.mock.contexts[n] as Element).tagName === 'BUTTON')
    expect((hop![0] as Keyframe[]).length).toBe(4)
  })

})

describe('ResultsAggregate’s switch presses', () => {
  beforeEach(() => {
    browser.preference.value = 'no-preference'
  })

  it.each([
    ['a mouse’s main button', 'pointerdown', { button: 0 }, 1],
    ['a mouse’s other button', 'pointerdown', { button: 2 }, 0],
    ['Space', 'keydown', { key: ' ' }, 1],
    ['Space held down', 'keydown', { key: ' ', repeat: true }, 0],
    ['another key', 'keydown', { key: 'a' }, 0]
  ])('sinks a switch under %s', async (_, event, init, sinks) => {
    const { played, wrapper } = await mounted()
    played.mockClear()
    await switchesOf(wrapper)[0]!.trigger(event, init)
    expect(played).toHaveBeenCalledTimes(sinks)
  })

  it('springs a held switch back once it is let go, and a switch never held not at all', async () => {
    const { played, wrapper } = await mounted()
    const [first, second]     = switchesOf(wrapper)
    await first!.trigger('pointerdown', { button: 0 })
    await first!.trigger('pointerdown', { button: 0 })
    await first!.trigger('pointerup')
    await second!.trigger('pointerup')
    expect(played.mock.calls.map(([keyframes]) => (keyframes as Keyframe[]).length)).toStrictEqual([2, 4])
  })

  it('plays nothing under reduced motion', async () => {
    browser.preference.value = 'reduce'
    const { played, wrapper } = await mounted()
    await switchesOf(wrapper)[0]!.trigger('pointerdown', { button: 0 })
    await switchesOf(wrapper)[0]!.trigger('click')
    expect(played).not.toHaveBeenCalled()
  })
})
