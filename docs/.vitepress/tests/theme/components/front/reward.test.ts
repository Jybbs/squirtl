// @vitest-environment happy-dom
import { type VueWrapper, enableAutoUnmount, mount }         from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { nextTick }                                          from 'vue'

import { TEMPO }              from '../../../../lib/front/reward.ts'
import { Player }             from '../../../../lib/game/player.ts'
import { IDENTITY }           from '../../../../lib/identity/identity.ts'
import { Chip }               from '../../../../theme/components/kit/chip.tsx'
import * as browser           from '../../../common/browser.ts'
import { Recorder, drawInto } from '../../../common/canvas.ts'
import * as pointer           from '../../../common/pointer.ts'

/**
 * A mounted widget beside the canvas recorder its screen draws into, the sight
 * a case shows it through, and the call that sizes its climb's box.
 */
interface Mounted {
  recorder : Recorder
  resize   : (width: number, height: number) => void
  sight    : browser.Sight
  wrapper  : VueWrapper
}

const { StoryReward } = await import('../../../../theme/components/front/reward.tsx')

/**
 * The climb's drawing, which every mark also being an SVG leaves the one SVG
 * that draws over its whole box.
 */
const DRAWING = 'svg.overflow-visible'

enableAutoUnmount(afterEach)

/**
 * Mounts the widget with its screen drawing into a recorder, or into nothing
 * where `drawn` is unset, each room's image decoding as `decoded` settles, and
 * the browser's `ResizeObserver` stood in for by one a case sizes the climb
 * through.
 */
async function mounted(
  drawn   : boolean             = true,
  decoded : () => Promise<void> = () => Promise.resolve()
): Promise<Mounted> {
  const recorder = new Recorder()
  drawInto(drawn ? recorder : null)
  vi.spyOn(HTMLImageElement.prototype, 'decode').mockImplementation(decoded)
  const resize  = browser.stubSize()
  const sight   = browser.stubSight()
  const wrapper = mount(StoryReward, { attachTo: document.body })
  await nextTick()
  return { recorder, resize, sight, wrapper }
}

/**
 * Reads the length of the spacing step the utility `utility` among `classes`
 * names, such as the 7 of `left-7`.
 */
function insetOf(classes: readonly string[], utility: string): number {
  const step = classes.find(each => each.startsWith(`${utility}-`))!.slice(utility.length + 1)
  return IDENTITY.lengths.spacing[step as keyof typeof IDENTITY.lengths.spacing]
}

/**
 * Reads the name, the note, and the value of every chip the widget sets, the
 * last press's first, then each term's.
 */
const chips = (wrapper: VueWrapper) => wrapper.findAllComponents(Chip).map(chip => {
  const { name, note, value } = chip.props()
  return [name, note, value]
})

beforeEach(() => {
  browser.preference.value = 'reduce'
  vi.useFakeTimers()
})

describe('StoryReward under reduced motion', () => {
  test('shows the episode’s end at once', async () => {
    const { recorder, sight, wrapper } = await mounted()

    sight.show(true)
    await nextTick()

    expect(pointer.sliderState(wrapper)).toStrictEqual(['163', 'Step 163 of 163, the return 0.91500'])
    expect(wrapper.text()).toContain('0.91500Step 163 of 163')
    expect(chips(wrapper).slice(0, 4)).toStrictEqual([
      ['The starter', null, '+0.60000'],
      ['New positions', '60 × 0.00025', '0.01500'],
      ['Milestones', '3 of 3', '0.30000'],
      ['The starter', 'Squirtle', '0.60000']
    ])
    expect(recorder.images.length).toBeGreaterThan(0)
  })

  test('draws the climb once measured, dimming each jump the step shown has not reached', async () => {
    const { resize, sight, wrapper } = await mounted()
    const before                     = wrapper.findAll(DRAWING).length

    resize(401, 298)
    await nextTick()
    const dimmed = () => wrapper.findAll('g.opacity-45').length
    const first  = dimmed()
    sight.show(true)
    await nextTick()

    expect([before, first, dimmed()]).toStrictEqual([0, 4, 0])
    expect(wrapper.get(DRAWING).attributes('viewBox')).toBe('0 0 401 298')
  })
})

describe('StoryReward’s layout', () => {
  test('insets the slider and the figures to the ends of the course the climb draws', async () => {
    const { resize, wrapper } = await mounted()

    resize(401, 298)
    await nextTick()
    const course  = wrapper.get('path.stroke-ahead').attributes('d')!
    const left    = Number(/^M([\d.]+)/u.exec(course)![1])
    const right   = 401 - Number(/H([\d.]+)V[\d.]+$/u.exec(course)![1])
    const control = wrapper.get('.cursor-ew-resize').classes()
    const figures = wrapper.get('.reward-chips.pointer-events-none').classes()

    expect([insetOf(control, 'left'), insetOf(control, 'right'), insetOf(figures, '@lg:left')])
      .toStrictEqual([left, right, left])
  })

  test('stretches the climb to the screen and drops its foot room only from the widget’s lg', async () => {
    const { wrapper } = await mounted()
    const box         = wrapper.get('.h-reward-climb')
    const pair        = wrapper.get('.reward-pair').classes()
    const keyed       = [...box.classes(), ...box.element.parentElement!.classList, ...pair]
      .filter(each => each.startsWith('@'))

    expect(keyed).toStrictEqual(['@lg:h-auto', '@max-lg:mb-6', '@lg:mb-6'])
  })
})

describe('StoryReward’s chips and key', () => {
  test('sets the key of the players’ hues and of what one press of each term pays', async () => {
    const { wrapper } = await mounted()

    expect(wrapper.findAll('ul > li').map(entry => entry.text())).toStrictEqual([
      'The agent', 'Random presses', 'New positions+0.00025', 'Milestones+0.10000', 'The starter+0.60000',
      'Already reached0.00000'
    ])
    expect(wrapper.text()).toBePublishedProse()
  })

  test('sets every chip in a list the sheet holds at least as wide as its widest chip', async () => {
    const { wrapper } = await mounted()
    const lists       = wrapper.findAllComponents(Chip).map(chip => chip.element.parentElement!.classList)

    expect(lists).toHaveLength(4)
    expect(lists.filter(list => !list.contains('reward-chips'))).toStrictEqual([])
  })
})

describe('StoryReward drawing its screen', () => {
  test('draws the screen as it mounts and again once the rooms’ images decode', async () => {
    const decoding     = Promise.withResolvers<void>()
    const { recorder } = await mounted(true, () => decoding.promise)
    const first        = recorder.images.length

    decoding.resolve()
    await vi.runAllTimersAsync()

    expect([first, recorder.images.length]).toStrictEqual([1, 2])
  })

  test('leaves the screen as it stands where a room’s image fails to decode', async () => {
    const { recorder } = await mounted(true, () => Promise.reject(new Error('undecodable')))

    await vi.runAllTimersAsync()

    expect(recorder.images).toHaveLength(1)
  })

  test('draws nothing where the canvas gives no context', async () => {
    const { recorder, sight } = await mounted(false)

    sight.show(true)
    await vi.runAllTimersAsync()

    expect(recorder.images).toStrictEqual([])
  })
})

describe('StoryReward playing', () => {
  beforeEach(() => {
    browser.preference.value = 'no-preference'
  })

  test('presses once the widget shows and again each beat', async () => {
    const { sight, wrapper } = await mounted()

    sight.show(true)
    await nextTick()
    const first = pointer.sliderState(wrapper)[0]
    vi.advanceTimersByTime(TEMPO.beat)
    await nextTick()

    expect([first, pointer.sliderState(wrapper)[0]]).toStrictEqual(['1', '2'])
  })

  test('rests on the starter, then plays the episode again from the bedroom', async () => {
    const { sight, wrapper } = await mounted()

    sight.show(true)
    vi.advanceTimersByTime(20_800)
    await nextTick()
    const ended = pointer.sliderState(wrapper)[0]
    vi.advanceTimersByTime(TEMPO.rest + 100)
    await nextTick()

    expect([ended, pointer.sliderState(wrapper)[0]]).toStrictEqual(['163', '1'])
  })

  test('ends every timer once it unmounts', async () => {
    const { sight, wrapper } = await mounted()
    const next               = vi.spyOn(Player.prototype, 'next')

    sight.show(true)
    wrapper.unmount()
    vi.advanceTimersByTime(5000)

    expect(next).toHaveBeenCalledTimes(1)
  })
})

describe('StoryReward held by a reader', () => {
  beforeEach(() => {
    browser.preference.value = 'no-preference'
  })

  test.each([
    [131, ['A milestone', null, '+0.10025']],
    [132, ['Following Oak', null, '0.00000']],
    [156, ['Two milestones', null, '+0.20025']]
  ])('seeks step %i under a press along the climb, holding the episode there', async (step, paid) => {
    const { sight, wrapper } = await mounted()
    const control            = pointer.controlOf(wrapper, 163)
    sight.show(true)

    await control.trigger('pointerenter', { pointerType: 'mouse' })
    await pointer.press(control, step)
    vi.advanceTimersByTime(1000)
    await nextTick()

    expect([pointer.sliderState(wrapper)[0], chips(wrapper)[0]]).toStrictEqual([String(step), paid])
  })

  test('holds the episode still while a mouse moves across the climb', async () => {
    const { sight, wrapper } = await mounted()
    const control            = pointer.controlOf(wrapper, 163)
    sight.show(true)
    await nextTick()

    const rested = pointer.sliderState(wrapper)[0]
    await pointer.sweep(control, [20, 80, 140])
    vi.advanceTimersByTime(1000)
    await nextTick()

    expect(pointer.sliderState(wrapper)[0]).toBe(rested)
  })
})

describe('StoryReward stepped by the keys', () => {
  beforeEach(() => {
    browser.preference.value = 'no-preference'
  })

  test('steps with the keys while the slider has focus, holding the episode until it loses it', async () => {
    const { sight, wrapper } = await mounted()
    const thumb              = wrapper.get('[role="slider"]')
    sight.show(true)

    await thumb.trigger('focusin')
    await thumb.trigger('keydown', { key: 'End' })
    await thumb.trigger('keydown', { key: 'ArrowLeft' })
    vi.advanceTimersByTime(1000)
    await nextTick()
    const held = pointer.sliderState(wrapper)
    await thumb.trigger('focusout')
    vi.advanceTimersByTime(200)
    await nextTick()

    expect([held, pointer.sliderState(wrapper)[0]])
      .toStrictEqual([['162', 'Step 162 of 163, the return 0.31500'], '163'])
  })
})
