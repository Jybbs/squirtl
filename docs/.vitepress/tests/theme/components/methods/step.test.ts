// @vitest-environment happy-dom
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi }    from 'vitest'
import { nextTick }                               from 'vue'

import * as step              from '../../../../lib/methods/step.ts'
import * as browser           from '../../../common/browser.ts'
import { Recorder, drawInto } from '../../../common/canvas.ts'
import * as pointer           from '../../../common/pointer.ts'

const { MethodsStep } = await import('../../../../theme/components/methods/step.tsx')

enableAutoUnmount(afterEach)

/**
 * Reads the line naming the step and the frame the sheet stands at.
 */
const status = (wrapper: ReturnType<typeof mount>): string => wrapper.get('.step-status').text()

describe('MethodsStep', () => {
  it('opens on the last frame of the last step, the key naming each mark and the frames it covers', () => {
    drawInto(null)
    const wrapper = mount(MethodsStep)

    expect([status(wrapper), pointer.sliderState(wrapper)]).toStrictEqual([
      'Step 10 of 10 · frame 17 of 17', ['169', 'Step 10, Left, frame 17 of 17']
    ])
    expect(wrapper.findAllComponents({ name: 'Chip' }).map(chip => chip.text()))
      .toStrictEqual(['Heldframes1–2', 'Readframe1 or 2', 'Not drawnframes1–16', 'Returnedframe17'])
    expect(wrapper.findAll('.visually-hidden').map(each => each.text())).toStrictEqual(step.STEPS.map(each =>
      ({ a: 'A', down: 'Down', left: 'Left', null: 'No press', right: 'Right', up: 'Up' })[String(each.press)]))
    expect(wrapper.text()).toBePublishedProse()
  })

  it('draws every frame of every step once the bedroom loads', async () => {
    const recorder = drawInto(new Recorder())
    mount(MethodsStep)
    await flushPromises()

    expect(recorder.images.length).toBeGreaterThanOrEqual(step.STEPS.length * step.FRAMES)
  })
})

describe('MethodsStep’s slider', () => {
  it('stands on the frame a press lands on, the row read down the sheet', async () => {
    drawInto(null)
    const wrapper = mount(MethodsStep, { attachTo: document.body })
    const control = wrapper.get("[data-part='control']")
    vi.spyOn(control.element, 'getBoundingClientRect').mockReturnValue({ height: 100, left: 0, top: 0, width: 170 } as DOMRect)
    control.element.setPointerCapture = () => {}

    await control.trigger('pointerdown', { button: 0, clientX: 25, clientY: 35, pointerId: 1, pointerType: 'mouse' })
    await control.trigger('pointermove', { buttons: 1, clientX: 165, clientY: 35, pointerType: 'mouse' })
    await control.trigger('pointermove', { buttons: 0, clientX: 5, clientY: 5, pointerType: 'mouse' })

    expect(status(wrapper)).toBe('Step 4 of 10 · frame 17 of 17')
  })

  it('steps back to the start of a row on Page Down', async () => {
    drawInto(null)
    const wrapper = mount(MethodsStep, { attachTo: document.body })
    const thumb   = wrapper.get('[role="slider"]')

    await thumb.trigger('focusin')
    await thumb.trigger('keydown', { key: 'PageDown' })
    await nextTick()

    expect(status(wrapper)).toBe('Step 10 of 10 · frame 1 of 17')
  })
})

describe('MethodsStep’s playback', () => {
  it('plays a frame a beat once it shows', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'performance', 'requestAnimationFrame', 'cancelAnimationFrame'] })
    drawInto(null)
    const sight   = browser.stubSight()
    const wrapper = mount(MethodsStep, { attachTo: document.body })
    await nextTick()

    sight.show(true)
    await nextTick()
    const first = status(wrapper)
    vi.advanceTimersByTime(step.TEMPO.tick - 1)
    await nextTick()
    const held  = status(wrapper)
    vi.advanceTimersByTime(1)
    await nextTick()

    expect([first, held, status(wrapper)])
      .toStrictEqual(['Step 1 of 10 · frame 1 of 17', 'Step 1 of 10 · frame 1 of 17', 'Step 1 of 10 · frame 2 of 17'])
    vi.useRealTimers()
  })

  it('rests on the frame PyBoy draws before the next step, and stands on the last frame under reduced motion', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'performance', 'requestAnimationFrame', 'cancelAnimationFrame'] })
    drawInto(null)
    const sight   = browser.stubSight()
    const wrapper = mount(MethodsStep, { attachTo: document.body })
    await nextTick()

    sight.show(true)
    vi.advanceTimersByTime((step.FRAMES - 1) * step.TEMPO.tick + step.TEMPO.rest - 1)
    await nextTick()
    const rested = status(wrapper)
    browser.preference.value = 'reduce'
    await nextTick()

    expect([rested, status(wrapper)]).toStrictEqual(['Step 1 of 10 · frame 17 of 17', 'Step 10 of 10 · frame 17 of 17'])
    vi.useRealTimers()
  })
})
