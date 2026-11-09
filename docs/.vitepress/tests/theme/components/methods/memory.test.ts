// @vitest-environment happy-dom
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi }     from 'vitest'
import { nextTick }                                from 'vue'

import { LAST, TRACE }        from '../../../../lib/methods/memory.ts'
import { fitOf }              from '../../../../lib/methods/memory/marks.ts'
import * as browser           from '../../../common/browser.ts'
import { Recorder, drawInto } from '../../../common/canvas.ts'
import * as pointer           from '../../../common/pointer.ts'

const { MethodsMemory } = await import('../../../../theme/components/methods/memory.tsx')

enableAutoUnmount(afterEach)

type Wrapper = ReturnType<typeof mount>

/**
 * Reads the sentence beneath the map, the longest sentence it is laid over left
 * out.
 */
const says = (wrapper: Wrapper): string => wrapper.get('.memory-says > span:last-child').text()

/**
 * Reads each chip of the bytes, its name beside the value it shows.
 */
const bytes = (wrapper: Wrapper): string[] => wrapper.findAll('.memory-bytes .memory-code').map(chip => chip.text())

/**
 * Moves a mouse onto the middle of the bedroom's square `at`, on a stage laid
 * out at the plate's own size.
 */
async function pointAt(wrapper: Wrapper, at: readonly [number, number]): Promise<void> {
  const stage = wrapper.get('.memory-stage')
  const fit   = fitOf('bedroom')
  vi.spyOn(stage.element, 'getBoundingClientRect').mockReturnValue({ left: 0, top: 0, width: 316 } as DOMRect)
  await stage.trigger('pointermove', { clientX: fit.left + (at[0] + 0.5) * fit.cell, clientY: fit.top + (at[1] + 0.5) * fit.cell })
}

describe('MethodsMemory', () => {
  it('opens on the bedroom at the reset, the bytes naming Blue’s square and no flag set', () => {
    drawInto(null)
    const wrapper = mount(MethodsMemory)

    expect([pointer.sliderState(wrapper), says(wrapper), bytes(wrapper)]).toStrictEqual([
      ['0', 'Step 0 of 163'], 'Step 0 stands on (26, 03, 06) in the bedroom.', ['wCurMap26', 'wXCoord03', 'wYCoord06', 'wEventFlags00 00']
    ])
    expect(wrapper.text()).toBePublishedProse()
  })

  it('reads the bytes of a pointed square, and the step’s again once the pointer leaves the map', async () => {
    drawInto(null)
    const wrapper = mount(MethodsMemory)

    await pointAt(wrapper, [5, 2])
    const pointed = [says(wrapper), bytes(wrapper)[1]!.slice(-2), bytes(wrapper)[2]!.slice(-2)]
    await pointAt(wrapper, [-1, 2])
    const off = says(wrapper)
    await pointAt(wrapper, [5, 2])
    await wrapper.get('.memory-stage').trigger('pointerleave')

    expect([pointed, off, says(wrapper)]).toStrictEqual([
      ['(26, 05, 02) is not reached by step 0, so the first step onto it pays 0.00025.', '05', '02'],
      'Step 0 stands on (26, 03, 06) in the bedroom.',
      'Step 0 stands on (26, 03, 06) in the bedroom.'
    ])
  })
})

describe('MethodsMemory’s marks', () => {
  it('picks out the key’s entry a mouse rests on, and holds the one pressed', async () => {
    drawInto(null)
    const wrapper = mount(MethodsMemory)
    const entries = wrapper.findAll('button[aria-pressed]')

    await entries[2]!.trigger('pointerenter', { pointerType: 'mouse' })
    const hovered = entries.map(entry => entry.classes().includes('opacity-45'))
    await entries[2]!.trigger('pointerleave')
    await entries[4]!.trigger('click')
    const pressed = entries.map(entry => entry.attributes('aria-pressed'))
    await entries[4]!.trigger('click')

    expect([hovered.filter(Boolean).length, pressed[4], entries[4]!.attributes('aria-pressed')]).toStrictEqual([4, 'true', 'false'])
  })

  it('draws the room, the squares reached, and the people once the maps load', async () => {
    vi.spyOn(HTMLImageElement.prototype, 'naturalWidth', 'get').mockReturnValue(2)
    vi.spyOn(HTMLImageElement.prototype, 'naturalHeight', 'get').mockReturnValue(2)
    const recorder = drawInto(new Recorder())
    mount(MethodsMemory)
    await flushPromises()
    await nextTick()

    expect([recorder.images.length > 0, recorder.marks.length > 0]).toStrictEqual([true, true])
  })

  it('dashes the row Oak appears at across Pallet Town before the episode reaches it', async () => {
    drawInto(null)
    const wrapper = mount(MethodsMemory, { attachTo: document.body })
    const pallet  = TRACE.findIndex(row => row.place === 'pallet')

    await pointer.press(pointer.controlOf(wrapper, LAST), pallet)
    await nextTick()

    const { cell, left, top, width } = fitOf('pallet')
    expect(wrapper.findAll('.memory-stage rect[stroke-dasharray="4 3"]').map(rect => [rect.attributes('x'), rect.attributes('y'), rect.attributes('width')])).toStrictEqual([
      [String(left), String(top + cell), String(width)]
    ])
  })
})

describe('MethodsMemory’s playback', () => {
  it('holds the episode at the step the arrow keys reach', async () => {
    drawInto(null)
    const wrapper = mount(MethodsMemory, { attachTo: document.body })
    const thumb   = wrapper.get('[role="slider"]')

    await thumb.trigger('focusin')
    await thumb.trigger('keydown', { key: 'ArrowRight' })
    await thumb.trigger('keydown', { key: 'ArrowRight' })
    await nextTick()

    expect([pointer.sliderState(wrapper), says(wrapper).slice(0, 6)]).toStrictEqual([['2', 'Step 2 of 163'], 'Step 2'])
  })

  it('fills each flag’s site in the lab once the episode reaches the starter', async () => {
    drawInto(null)
    const wrapper = mount(MethodsMemory, { attachTo: document.body })
    const thumb   = wrapper.get('[role="slider"]')

    await thumb.trigger('focusin')
    await thumb.trigger('keydown', { key: 'End' })
    await nextTick()

    expect([wrapper.findAll('.memory-pulse').length, bytes(wrapper)[0], says(wrapper).endsWith('which ends the episode.')]).toStrictEqual([3, 'wCurMap28', true])
  })

  it('plays frame by frame once it shows, and stands on the starter under reduced motion', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'performance', 'requestAnimationFrame', 'cancelAnimationFrame'] })
    drawInto(null)
    const sight   = browser.stubSight()
    const wrapper = mount(MethodsMemory, { attachTo: document.body })
    await nextTick()

    sight.show(true)
    vi.advanceTimersByTime(2000)
    await nextTick()
    const playing = Number(pointer.sliderState(wrapper)[0])
    browser.preference.value = 'reduce'
    await nextTick()

    expect([playing > 0, pointer.sliderState(wrapper)[0]]).toStrictEqual([true, String(LAST)])
    vi.useRealTimers()
  })
})
