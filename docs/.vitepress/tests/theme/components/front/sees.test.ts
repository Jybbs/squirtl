// @vitest-environment happy-dom
import { type VueWrapper, enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, test, vi }        from 'vitest'

import * as sees              from '../../../../lib/front/sees.ts'
import { SEES_TEMPO }         from '../../../../lib/front/sees/playthrough.ts'
import { SCREEN }             from '../../../../lib/game/screen.ts'
import { hexOf, rgbOf }       from '../../../../lib/identity/identity.ts'
import { count, stepText }    from '../../../../lib/widgets/numbers.ts'
import * as browser           from '../../../common/browser.ts'
import { Recorder, drawInto } from '../../../common/canvas.ts'
import * as pointer           from '../../../common/pointer.ts'

const { StorySees } = await import('../../../../theme/components/front/sees.tsx')

/**
 * The presses the widget's episode takes to reach the starter.
 */
const last = sees.stepsOf()

/**
 * Reads the red, green, and blue of Athens Gray, the game's white.
 */
const white = rgbOf(hexOf('ground'))

/**
 * A stand-in for a canvas's 2D context that records what the widget draws and
 * each view it puts, and reads every screen back in the game's white.
 */
class Pixels extends Recorder {
  readonly screen = new Uint8ClampedArray(SCREEN.width * SCREEN.height * 4)

  constructor() {
    super()
    for (let i = 0; i < this.screen.length; i += 4) this.screen.set([...white, 255], i)
  }

  /**
   * Reads the screen back in the game's white.
   */
  getImageData(): ImageData {
    return { data: this.screen } as ImageData
  }
}

/**
 * Reads the values the flags' chips show, in the order the network reads the
 * flags.
 */
const flagValues = (wrapper: VueWrapper): string[] =>
  wrapper.findAll('.sees-flags .ml-auto').map(each => each.text())

/**
 * Reads the figure beneath the label of the caption in the grid area the class
 * `place` names.
 */
const figureOf = (wrapper: VueWrapper, place: string): string => wrapper.findAll(`.${place} span`)[1]!.text()

/**
 * Reads the step the screen's caption names.
 */
const shownStep = (wrapper: VueWrapper): string => figureOf(wrapper, 'sees-screen-say')

/**
 * Writes the words naming step `at` of the widget's episode.
 */
const stepAt = (at: number): string => stepText(at, last)

/**
 * Mounts the widget with every canvas drawing into one recorder, lets the
 * rooms' images load, and returns the wrapper beside the recorder and the sight
 * a case shows the widget through.
 */
async function mounted(): Promise<{ pixels: Pixels, sight: browser.Sight, wrapper: VueWrapper }> {
  const sight   = browser.stubSight()
  const pixels  = drawInto(new Pixels())
  const wrapper = mount(StorySees, { attachTo: document.body })
  await flushPromises()
  return { pixels, sight, wrapper }
}

beforeEach(() => {
  vi.useFakeTimers({
    toFake: ['setTimeout', 'clearTimeout', 'performance', 'requestAnimationFrame', 'cancelAnimationFrame']
  })
})

enableAutoUnmount(afterEach)

describe('StorySees at rest', () => {
  test('draws the first step once the rooms load, each gray frame and the grid put as pixels', async () => {
    const { pixels, wrapper } = await mounted()

    expect(shownStep(wrapper)).toBe(stepAt(0))
    expect(pixels.views).toHaveLength(sees.OBSERVING.stack + 1)
    expect([...pixels.views[0]!.data.subarray(0, 3)]).toStrictEqual(white)
    expect(flagValues(wrapper)).toStrictEqual(['0', '0', '0', '0'])
  })

  test('leaves every canvas blank where a room’s image fails to decode', async () => {
    vi.spyOn(HTMLImageElement.prototype, 'decode').mockRejectedValue(new Error('undecodable'))
    const { pixels, wrapper } = await mounted()

    expect([pixels.images, pixels.views, shownStep(wrapper)]).toStrictEqual([[], [], stepAt(0)])
  })

  test('tags the frames newest last and captions each drawing with its shape and bytes', async () => {
    const { wrapper }            = await mounted()
    const bytes                  = sees.bytesOf()
    const { frame, grid, stack } = sees.OBSERVING

    expect(wrapper.findAll('span.self-end').map(each => each.text()))
      .toStrictEqual(['t − 3', 't − 2', 't − 1', 't'])
    expect(wrapper.findAll('canvas').map(each => each.attributes('aria-label')).slice(1, 5)).toStrictEqual([
      'The frame 3 steps before', 'The frame 2 steps before', 'The frame 1 step before',
      'The frame of this step'
    ])
    expect([figureOf(wrapper, 'sees-frames-say'), figureOf(wrapper, 'sees-grid-say')]).toStrictEqual([
      `${stack} × ${frame.height} × ${frame.width}, newest last · ${count(bytes.frames)} bytes`,
      `${grid} × ${grid}, Blue at the center · ${count(bytes.grid)} bytes`
    ])
    expect(wrapper.text()).toBePublishedProse()
  })

  test('shows the end at once, every flag set, where the reader asks for reduced motion', async () => {
    browser.preference.value = 'reduce'
    const { sight, wrapper } = await mounted()

    sight.show(true)
    await flushPromises()

    expect([shownStep(wrapper), flagValues(wrapper)]).toStrictEqual([stepAt(last), ['1', '1', '1', '1']])
    expect(['bg-amethyst-1', 'bg-heath-1'].map(tint => wrapper.findAll(`.sees-flags .${tint}`).length))
      .toStrictEqual([1, 3])
  })
})

describe('StorySees playing', () => {
  test('plays a press a beat once it shows, each gray frame dropping in by the next beat', async () => {
    const { sight, wrapper } = await mounted()
    const seek               = vi.spyOn(sees.Observation.prototype, 'seek')

    sight.show(true)
    const first = shownStep(wrapper)
    await vi.advanceTimersByTimeAsync(SEES_TEMPO.beat)

    expect([first, shownStep(wrapper), seek.mock.calls]).toStrictEqual([stepAt(0), stepAt(1), []])
  })

  test('rests on the starter, then plays again from the bedroom', async () => {
    const { sight, wrapper } = await mounted()

    sight.show(true)
    await vi.advanceTimersByTimeAsync((last + 1) * SEES_TEMPO.beat)
    const end = shownStep(wrapper)
    await vi.advanceTimersByTimeAsync(SEES_TEMPO.rest - SEES_TEMPO.beat)

    expect([end, shownStep(wrapper)]).toStrictEqual([stepAt(last), stepAt(0)])
  })
})

describe('StorySees held by a reader', () => {
  test('drops the frames in while a resting mouse holds the step, and plays on once it leaves', async () => {
    const { sight, wrapper } = await mounted()
    const control            = pointer.controlOf(wrapper, last)

    sight.show(true)
    await pointer.sweep(control, [20, 100, 140])
    await vi.advanceTimersByTimeAsync(SEES_TEMPO.beat * 4)
    const held = shownStep(wrapper)
    await control.trigger('pointerleave', { pointerType: 'mouse' })
    await vi.advanceTimersByTimeAsync(SEES_TEMPO.beat * 2)

    expect([held, shownStep(wrapper)]).toStrictEqual([stepAt(1), stepAt(3)])
  })

  test('seeks the step a press on the frames lands on', async () => {
    const { wrapper } = await mounted()
    const control     = pointer.controlOf(wrapper, last)

    await pointer.press(control, 100)

    expect(pointer.sliderState(wrapper)[0]).toBe('100')
  })

  test('steps the observation with the arrow keys once the frames have focus', async () => {
    const { wrapper } = await mounted()
    const thumb       = wrapper.get('[role="slider"]')

    await thumb.trigger('focusin')
    await thumb.trigger('keydown', { key: 'ArrowRight' })

    expect([shownStep(wrapper), pointer.sliderState(wrapper)[1]]).toStrictEqual([stepAt(1), stepAt(1)])
  })
})

describe('StorySees unmounted', () => {
  test('ends its timers and its frame loop, pressing and drawing nothing after', async () => {
    const { pixels, sight, wrapper } = await mounted()
    const next                       = vi.spyOn(sees.Observation.prototype, 'next')
    vi.clearAllTimers()

    sight.show(true)
    await vi.advanceTimersByTimeAsync(SEES_TEMPO.beat / 2)
    wrapper.unmount()
    const ended = vi.getTimerCount()
    const drawn = pixels.images.length
    await vi.advanceTimersByTimeAsync(SEES_TEMPO.beat * 4)

    expect([ended, next.mock.calls.length, pixels.images.length]).toStrictEqual([0, 1, drawn])
  })
})
