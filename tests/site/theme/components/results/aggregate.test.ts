// @vitest-environment happy-dom
import { type VueWrapper, enableAutoUnmount, mount }                        from '@vue/test-utils'
import { type MockInstance, afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createSSRApp, h, nextTick }                                          from 'vue'
import { renderToString }                                                     from 'vue/server-renderer'

import * as browser from '../../../common/browser.ts'

/**
 * Whether the stand-in below holds the runs the repository commits, five per
 * group under seeds 1 to 5, or no run at all.
 */
const held = vi.hoisted(() => ({ runs: true }))

vi.mock('../../../../../docs/.vitepress/lib/results/results.ts', async original => {
  const module = await original<typeof import('../../../../../docs/.vitepress/lib/results/results.ts')>()
  const none   = { comparisons: [], random: null, runs: [] }
  const shown  = () => (held.runs ? module.COMMITTED : none) as typeof module.COMMITTED
  return {
    ...module,
    get COMMITTED() { return shown() },
    groupsOf: (results = shown()) => module.groupsOf(results)
  }
})

const { ResultsAggregate } = await import(
  '../../../../../docs/.vitepress/theme/components/results/aggregate.tsx'
)

enableAutoUnmount(afterEach)

/**
 * A widget mounted into the document and the spy standing in for every
 * animation an element plays.
 */
interface Mounted {
  played  : MockInstance<Element['animate']>
  wrapper : VueWrapper
}

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
    expect(textsOf((await mounted()).wrapper).slice(3, 9))
      .toStrictEqual(['Random presses 21% [14, 31]', 'DQN', 'Bedroom', '0%', '[0, 0]', 'PPO'])
  })

  it.each([
    [688, 0],
    [300, 10]
  ])('sets each column’s interval at %d wide on %d lines of its own', async (width, lines) => {
    expect((await mounted(width)).wrapper.findAll('svg tspan[x]')).toHaveLength(lines)
  })

  it('takes over the markup the server renders, each figure in a node of its own', async () => {
    const widget   = { render: () => h(ResultsAggregate) }
    const hydrated = createSSRApp(widget)
    const root     = document.createElement('div')
    const warned   = vi.spyOn(console, 'warn').mockImplementation(() => {})
    root.innerHTML = await renderToString(createSSRApp(widget))
    document.body.append(root)
    hydrated.mount(root)
    hydrated.unmount()
    expect(warned).not.toHaveBeenCalled()
  })

  it('names each column to a screen reader with its figures', async () => {
    const { wrapper } = await mounted()
    expect(wrapper.get('[role="img"]').attributes('aria-label')).toMatch(
      /^Deep Q-network \(DQN\), from the bedroom: interquartile mean 0%, 95% interval 0 to 0% over 5 runs, /u
    )
  })

})

describe('ResultsAggregate’s seeds', () => {
  it('draws every figure again from the seeds a reader keeps', async () => {
    const { wrapper } = await mounted()
    await switchesOf(wrapper)[3]!.trigger('click')
    expect([
      wrapper.get('span').text(),
      textsOf(wrapper)[3],
      runGroupsOf(wrapper).filter(run => run.find('.fill-quiet').exists()).length
    ]).toStrictEqual(['Seeds kept, 4 runs each', 'Random presses 18% [13, 27]', 5])
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

describe('ResultsAggregate’s switch keys', () => {
  it.each([
    ['down the side from the container’s small width', 688, 'vertical', 'ArrowDown', 1],
    ['across beneath the plot below it', 300, 'horizontal', 'ArrowRight', 1],
    ['nowhere on the cross axis below it', 300, 'horizontal', 'ArrowDown', 0]
  ])('moves focus through the switches %s', async (_, width, orientation, key, focused) => {
    const { wrapper } = await mounted(width)
    const switches    = switchesOf(wrapper)
    const first       = switches[0]!.element as HTMLElement
    first.focus()
    await switches[0]!.trigger('keydown', { key })
    await new Promise(requestAnimationFrame)
    expect([
      wrapper.get('ul[aria-label="Seeds kept"]').attributes('data-orientation'),
      switches.findIndex(each => each.element === document.activeElement)
    ]).toStrictEqual([orientation, focused])
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

  it('settles random presses’ band two thirds of the way through its glide', async () => {
    const { played, wrapper } = await mounted()
    played.mockClear()
    await switchesOf(wrapper)[3]!.trigger('click')
    await nextTick()
    const band = played.mock.contexts.findIndex(each => (each as Element).classList.contains('text-random'))
    expect(played.mock.calls[band]![1]).toStrictEqual({ delay: 400, duration: 450, easing: 'ease-out' })
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

describe('ResultsAggregate’s switch releases', () => {
  beforeEach(() => {
    browser.preference.value = 'no-preference'
  })

  it.each([
    ['Enter let go', 'keydown', { key: 'Enter' }, 'keyup', { key: 'Enter' }],
    ['Space let go', 'keydown', { key: ' ' }, 'keyup', { key: ' ' }],
    ['focus moving away', 'keydown', { key: ' ' }, 'blur', {}],
    ['a pointer leaving', 'pointerdown', { button: 0 }, 'pointerleave', {}],
    ['a pointer cancelled', 'pointerdown', { button: 0 }, 'pointercancel', {}]
  ])('springs a sunk switch back under %s', async (_, down, sunk, up, release) => {
    const { played, wrapper } = await mounted()
    played.mockClear()
    await switchesOf(wrapper)[0]!.trigger(down, sunk)
    await switchesOf(wrapper)[0]!.trigger(up, release)
    expect(played.mock.calls.map(([keyframes]) => (keyframes as Keyframe[]).length)).toStrictEqual([2, 4])
  })
})
