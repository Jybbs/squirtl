// @vitest-environment happy-dom
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi }    from 'vitest'
import { nextTick }                               from 'vue'

import { FRAME }              from '../../../../lib/game/screen.ts'
import * as reach             from '../../../../lib/methods/reach.ts'
import * as browser           from '../../../common/browser.ts'
import { Recorder, drawInto } from '../../../common/canvas.ts'
import * as pointer           from '../../../common/pointer.ts'

const { MethodsReach } = await import('../../../../theme/components/methods/reach.tsx')

enableAutoUnmount(afterEach)

/**
 * Reads the line naming the pass training stands at.
 */
const status = (wrapper: ReturnType<typeof mount>): string => wrapper.get('.reach-status').text()

/**
 * A canvas reading back a room of two pixels by two in the Game Boy's four
 * shades.
 */
class Shaded extends Recorder {
  getImageData(): ImageData {
    return { data: new Uint8ClampedArray([255, 255, 255, 255, 170, 170, 170, 255, 85, 85, 85, 255, 0, 0, 0, 255]) } as ImageData
  }
}

describe('MethodsReach', () => {
  it('opens before training on four screens under the learners, the key naming Blue, Oak, and the pad', () => {
    drawInto(null)
    const wrapper = mount(MethodsReach)

    expect([
      status(wrapper),
      pointer.sliderState(wrapper),
      wrapper.findAll('figcaption').map(each => each.text()),
      wrapper.findAll('canvas').length
    ]).toStrictEqual([
      'Before training', ['0', 'Before training'], ['Online', 'Copy', 'No copy', 'Odds'], 4
    ])
    expect(wrapper.text()).toBePublishedProse()
  })

  it('draws every screen once Pallet Town loads', async () => {
    vi.spyOn(HTMLImageElement.prototype, 'naturalWidth', 'get').mockReturnValue(2)
    vi.spyOn(HTMLImageElement.prototype, 'naturalHeight', 'get').mockReturnValue(2)
    const recorder = drawInto(new Shaded())
    mount(MethodsReach)
    await flushPromises()

    expect([recorder.images.length, recorder.views.length]).toStrictEqual([1 + 4, 2 * 4])
  })

  it('fills each screen with the ground where training moves before Pallet Town loads', async () => {
    vi.spyOn(HTMLImageElement.prototype, 'decode').mockReturnValue(new Promise(() => {}))
    const recorder = drawInto(new Recorder())
    const thumb    = mount(MethodsReach).get('[role="slider"]')

    await thumb.trigger('focusin')
    await thumb.trigger('keydown', { key: 'ArrowRight' })
    await nextTick()

    expect(recorder.marks).toStrictEqual(Array.from({ length: 4 }, () => expect.objectContaining({ height: 9 * 16, width: 3 * 16, x: 0, y: 0 })))
  })
})

describe('MethodsReach’s playback', () => {
  it('holds training after the pass the arrow keys reach', async () => {
    drawInto(null)
    const wrapper = mount(MethodsReach, { attachTo: document.body })
    const thumb   = wrapper.get('[role="slider"]')

    await thumb.trigger('focusin')
    await thumb.trigger('keydown', { key: 'ArrowRight' })
    await thumb.trigger('keydown', { key: 'ArrowRight' })
    await nextTick()

    expect([status(wrapper), pointer.sliderState(wrapper)]).toStrictEqual(['Pass 2 of 8', ['2', 'After pass 2 of 8']])
  })

  it('plays on the Game Boy’s frame clock once it shows, and stands after the last pass under reduced motion', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'performance', 'requestAnimationFrame', 'cancelAnimationFrame'] })
    drawInto(null)
    const sight   = browser.stubSight()
    const wrapper = mount(MethodsReach, { attachTo: document.body })
    await nextTick()

    sight.show(true)
    vi.advanceTimersByTime((reach.LINE.start + 1) * FRAME)
    await nextTick()
    const playing = status(wrapper)
    browser.preference.value = 'reduce'
    await nextTick()

    expect([playing, status(wrapper)]).toStrictEqual(['Pass 1 of 8', 'Pass 8 of 8'])
    vi.useRealTimers()
  })
})
