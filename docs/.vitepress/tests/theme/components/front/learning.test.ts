// @vitest-environment happy-dom
import { type VueWrapper, enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, test, vi }        from 'vitest'
import { nextTick }                                                 from 'vue'

import { walksOf }            from '../../../../lib/front/learning.ts'
import { STRIP }              from '../../../../lib/front/learning/strip.ts'
import { battlePhases }       from '../../../../lib/front/learning/transition.ts'
import { PLAY }               from '../../../../lib/front/learning/walks.ts'
import * as browser           from '../../../common/browser.ts'
import { Recorder, drawInto } from '../../../common/canvas.ts'
import * as pointer           from '../../../common/pointer.ts'

const { StoryLearning } = await import('../../../../theme/components/front/learning.tsx')

/**
 * The presses each walk the widget plays takes.
 */
const PRESSES = walksOf().map(moment => moment.presses)

/**
 * Mounts the widget with its canvas drawing into a recorder once the town's
 * image has loaded, and returns the wrapper beside the recorder and the sight a
 * case shows it through.
 */
async function mounted(): Promise<{ screen: Recorder, sight: browser.Sight, wrapper: VueWrapper }> {
  const screen  = drawInto(new Recorder())
  const sight   = browser.stubSight()
  const wrapper = mount(StoryLearning, { attachTo: document.body })
  await flushPromises()
  return { screen, sight, wrapper }
}

/**
 * Reads the presses each walk's button shows.
 */
const valuesOf = (wrapper: VueWrapper): string[] =>
  wrapper.findAll('button').map(button => button.findAll('span').at(-1)!.text())

beforeEach(() => {
  browser.preference.value = 'reduce'
  vi.useFakeTimers({
    toFake: ['cancelAnimationFrame', 'clearTimeout', 'performance', 'requestAnimationFrame', 'setTimeout']
  })
})

enableAutoUnmount(afterEach)

describe('StoryLearning playing', () => {
  test('shows every walk’s end at once where the reader asks for reduced motion', async () => {
    const { sight, wrapper } = await mounted()

    sight.show(true)
    await nextTick()
    const [now, text] = pointer.sliderState(wrapper)

    expect(valuesOf(wrapper)).toStrictEqual(PRESSES.map(String))
    expect(now).toBe('204')
    expect(text).toMatch(/have reached the north edge$/u)
    expect(wrapper.get('text.font-medium').text()).toBe('204 presses')
  })

  test('sets every walk off together a press at a time, each stopping where it ends', async () => {
    browser.preference.value = 'no-preference'
    const { sight, wrapper } = await mounted()

    sight.show(true)
    vi.advanceTimersByTime(PLAY.press * 19)
    await nextTick()

    expect(valuesOf(wrapper)).toStrictEqual(['20', '20', '20', '18'])
    expect(pointer.sliderState(wrapper)[0]).toBe('20')
  })

  test('ends each loop in the transition into a wild battle, setting the walks off beneath it', async () => {
    browser.preference.value = 'no-preference'
    const { sight, wrapper } = await mounted()

    sight.show(true)
    vi.advanceTimersByTime(PLAY.press * 203 + 3200)
    await nextTick()
    const ended = valuesOf(wrapper)
    vi.advanceTimersByTime(battlePhases.circle + 100)
    await nextTick()
    const covered = valuesOf(wrapper)
    vi.advanceTimersByTime(battlePhases.end - battlePhases.circle + PLAY.press * 3)
    await nextTick()

    expect([ended, covered]).toStrictEqual([PRESSES.map(String), ['0', '0', '0', '0']])
    expect(Number(valuesOf(wrapper)[0])).toBeGreaterThan(0)
  })
})

describe('StoryLearning clock', () => {
  test('holds the clock still while a mouse moves along the strip', async () => {
    browser.preference.value = 'no-preference'
    const { sight, wrapper } = await mounted()
    const control            = pointer.controlOf(wrapper, 200)

    sight.show(true)
    await nextTick()
    const rested = valuesOf(wrapper)
    await pointer.sweep(control, [20, 100, 180])
    vi.advanceTimersByTime(1000)
    await nextTick()

    expect(valuesOf(wrapper)).toStrictEqual(rested)
  })

  test('sets the clock at the press a press along the strip lands on', async () => {
    const { wrapper } = await mounted()
    const control     = pointer.controlOf(wrapper, 200)

    await pointer.press(control, 100)

    expect(valuesOf(wrapper)).toStrictEqual(['102', '102', '50', '18'])
  })

  test('moves the clock with the keys once the strip has focus', async () => {
    const { sight, wrapper } = await mounted()
    const thumb              = wrapper.get('[role="slider"]')

    sight.show(true)
    await thumb.trigger('focusin')
    await thumb.trigger('keydown', { key: 'Home' })

    expect([valuesOf(wrapper), pointer.sliderState(wrapper)[0]]).toStrictEqual([['0', '0', '0', '0'], '0'])
  })
})

describe('StoryLearning picking', () => {
  test('picks out the walk a mouse points at along the strip, dimming every other Blue', async () => {
    const { screen, wrapper } = await mounted()
    const strip               = wrapper.get('.px-3')

    await strip.trigger('pointermove', { clientY: STRIP.top + STRIP.row * 2 + 1, pointerType: 'mouse' })
    const picked = wrapper.findAll('button').map(button => button.classes('opacity-45'))
    const dimmed = screen.marks.some(mark => mark.alpha === PLAY.dim)
    await strip.trigger('pointerleave')

    expect([picked, dimmed]).toStrictEqual([[true, true, false, true], true])
    expect(wrapper.findAll('button').map(button => button.classes('opacity-45')))
      .not.toContain(true)
  })

  test.each([
    ['a touch on a band', '.px-3', 'pointermove', { clientY: STRIP.top, pointerType: 'touch' }],
    ['a mouse above every band', '.px-3', 'pointermove', { clientY: 0, pointerType: 'mouse' }],
    ['a touch on a button', 'button', 'pointerenter', { pointerType: 'touch' }]
  ])('leaves the pick alone for %s', async (_, selector, type, event) => {
    const { wrapper } = await mounted()

    await wrapper.get(selector).trigger(type, event)

    expect(wrapper.findAll('button').map(button => button.classes('opacity-45')))
      .not.toContain(true)
  })

  test('picks out a walk while a mouse rests on its button, and keeps it picked once pressed', async () => {
    const { wrapper } = await mounted()
    const second      = wrapper.findAll('button')[1]!

    await second.trigger('pointerenter', { pointerType: 'mouse' })
    const hovered = wrapper.findAll('button').map(button => button.classes('opacity-45'))
    await second.trigger('click')
    await second.trigger('pointerleave')
    const pressed = [second.attributes('aria-pressed'), wrapper.findAll('button')[0]!.classes('opacity-45')]
    await second.trigger('click')

    expect([hovered, pressed, second.attributes('aria-pressed')]).toStrictEqual([
      [true, false, true, true], ['true', true], 'false'
    ])
  })
})

describe('StoryLearning lifetime', () => {
  test('plays on undrawn where the canvas gives no drawing context', async () => {
    drawInto(null)
    const sight   = browser.stubSight()
    const wrapper = mount(StoryLearning, { attachTo: document.body })
    await flushPromises()

    sight.show(true)
    await wrapper.findAll('button')[0]!.trigger('click')

    expect(valuesOf(wrapper)).toStrictEqual(PRESSES.map(String))
  })

  test('reads no town once it unmounts before the town’s image loads', async () => {
    const getContext = vi.spyOn(HTMLCanvasElement.prototype, 'getContext')
    browser.stubSight()
    mount(StoryLearning, { attachTo: document.body }).unmount()
    await flushPromises()

    expect(getContext).not.toHaveBeenCalled()
  })

  test('leaves the town undrawn where its image fails to decode', async () => {
    vi.spyOn(HTMLImageElement.prototype, 'decode').mockRejectedValue(new Error('undecodable'))
    const { screen } = await mounted()

    expect(screen.views).toStrictEqual([])
  })

  test('draws nothing more once it unmounts', async () => {
    browser.preference.value         = 'no-preference'
    const { screen, sight, wrapper } = await mounted()
    sight.show(true)
    vi.advanceTimersByTime(PLAY.press * 3)
    const views = screen.views.length

    wrapper.unmount()
    vi.advanceTimersByTime(PLAY.press * 20)

    expect(screen.views).toHaveLength(views)
  })
})

describe('StoryLearning words', () => {
  test('names its view, its strip, its clock, and its key in published prose', async () => {
    const { wrapper } = await mounted()
    const names       = [
      wrapper.get('canvas').attributes('aria-label')!,
      wrapper.get('svg[role="img"]').attributes('aria-label')!,
      wrapper.get('[role="slider"]').attributes('aria-label')!,
      ...wrapper.findAll('button').map(button => button.attributes('aria-label')!),
      wrapper.text()
    ]

    expect(names).not.toContain('')
    for (const name of names) expect(name).toBePublishedProse()
  })
})
