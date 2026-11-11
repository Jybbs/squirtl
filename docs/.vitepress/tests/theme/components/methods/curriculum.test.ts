// @vitest-environment happy-dom
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi }     from 'vitest'
import { nextTick }                                from 'vue'

import * as curriculum        from '../../../../lib/methods/curriculum.ts'
import { placeOf }            from '../../../../lib/methods/curriculum/lanes.ts'
import * as browser           from '../../../common/browser.ts'
import { Recorder, drawInto } from '../../../common/canvas.ts'
import * as pointer           from '../../../common/pointer.ts'

vi.mock('../../../../lib/widgets/still.ts', async original => {
  const { still } = await original<typeof import('../../../../lib/widgets/still.ts')>()
  return { still: vi.fn<typeof still>(still) }
})

const { still }             = await import('../../../../lib/widgets/still.ts')
const { MethodsCurriculum } = await import('../../../../theme/components/methods/curriculum.tsx')

enableAutoUnmount(afterEach)

/**
 * Reads each lane's phase and the words beside its screen.
 */
const lanes = (wrapper: ReturnType<typeof mount>): string[][] =>
  wrapper.findAll('.curriculum-lane').map(lane => [lane.attributes('data-phase')!, lane.findAll('span').at(-1)!.text()])

/**
 * Reads where each lane's screen stands along its track.
 */
const screens = (wrapper: ReturnType<typeof mount>): string[] =>
  wrapper.findAll<HTMLElement>('.curriculum-lane .curriculum-glide.relative').map(each => each.element.style.transform)

/**
 * Lays a lane out on a track 600 pixels wide, as a case reports it, with the
 * screen and the far figure as wide as happy-dom measures them.
 */
const at = (start: number, end: number) => placeOf({ far: 0, screen: 0, track: 600 }, start, end, 'right')

const FAKED = ['setTimeout', 'clearTimeout', 'performance', 'requestAnimationFrame', 'cancelAnimationFrame'] as const

describe('MethodsCurriculum', () => {
  it('opens on the last batch, every lane’s agent in the bedroom, over the places of the recording', () => {
    drawInto(null)
    const wrapper = mount(MethodsCurriculum)
    const last    = curriculum.BATCHES - 1

    expect(lanes(wrapper)).toStrictEqual(curriculum.SEGMENTS.map((_, k) => ['agent', curriculum.farOf(last, k)]))
    expect(wrapper.findAll('.curriculum-place').map(each => each.text())).toStrictEqual(curriculum.STRETCHES.map(each => each.name))
    expect(pointer.sliderState(wrapper)).toStrictEqual([String(last), curriculum.describe(last)])
    expect(wrapper.text()).toBePublishedProse()
  })

})

describe('MethodsCurriculum’s lanes', () => {
  it('lands each screen where its lane lays it out, at once on its first layout and on every new width', async () => {
    drawInto(null)
    const resize  = browser.stubSize()
    const wrapper = mount(MethodsCurriculum, { attachTo: document.body })
    await nextTick()
    vi.mocked(still).mockClear()

    resize(600, 80)
    await flushPromises()

    expect(screens(wrapper)).toStrictEqual(curriculum.SEGMENTS.map(each => `translateX(${at(0, each.end).screen}px)`))
    expect(wrapper.findAll<HTMLElement>('.curriculum-glide.bg-denim-mark').map(each => each.element.style.width))
      .toStrictEqual(curriculum.SEGMENTS.map(each => `${Number(at(0, each.end).reach.toFixed(6))}px`))
    expect(vi.mocked(still)).toHaveBeenCalledTimes(curriculum.SEGMENTS.length)
  })

  it('glides each screen to its start in the batch the slider names', async () => {
    drawInto(null)
    const resize  = browser.stubSize()
    const wrapper = mount(MethodsCurriculum, { attachTo: document.body })
    await nextTick()
    resize(600, 80)
    await flushPromises()
    vi.mocked(still).mockClear()
    const thumb   = wrapper.get('[role="slider"]')

    await thumb.trigger('focusin')
    await thumb.trigger('keydown', { key: 'Home' })
    await flushPromises()

    expect(screens(wrapper)).toStrictEqual(curriculum.RUN[0]!.map((shown, k) => `translateX(${at(shown.start, curriculum.SEGMENTS[k]!.end).screen}px)`))
    expect([vi.mocked(still).mock.calls.length, lanes(wrapper).map(([phase]) => phase)]).toStrictEqual([0, curriculum.SEGMENTS.map(() => 'agent')])
  })

  it('draws every lane’s screen once the rooms load', async () => {
    const recorder = drawInto(new Recorder())
    const moved    = vi.spyOn(recorder, 'setTransform')
    mount(MethodsCurriculum)
    await flushPromises()

    expect(moved).toHaveBeenCalledTimes(2 * curriculum.SEGMENTS.length)
  })
})

describe('MethodsCurriculum’s playback', () => {
  it('replays the recording in gray to every start once it shows, then hands each screen to the agent', async () => {
    vi.useFakeTimers({ toFake: [...FAKED] })
    drawInto(null)
    const sight   = browser.stubSight()
    const wrapper = mount(MethodsCurriculum, { attachTo: document.body })
    await nextTick()

    sight.show(true)
    await nextTick()
    vi.advanceTimersByTime(curriculum.TIMING.replay / 2)
    await nextTick()
    const replaying = lanes(wrapper).map(([phase]) => phase)
    vi.advanceTimersByTime(curriculum.TIMING.replay)
    await nextTick()

    expect([pointer.sliderState(wrapper)[0], replaying, lanes(wrapper).map(([phase]) => phase)])
      .toStrictEqual(['0', curriculum.SEGMENTS.map(() => 'recording'), curriculum.SEGMENTS.map(() => 'agent')])
    vi.useRealTimers()
  })

  it('stands on the last batch under reduced motion', async () => {
    vi.useFakeTimers({ toFake: [...FAKED] })
    drawInto(null)
    const sight   = browser.stubSight()
    const wrapper = mount(MethodsCurriculum, { attachTo: document.body })
    await nextTick()

    sight.show(true)
    vi.advanceTimersByTime(curriculum.TIMING.replay / 2)
    await nextTick()
    browser.preference.value = 'reduce'
    await nextTick()

    expect([pointer.sliderState(wrapper)[0], lanes(wrapper).map(([phase]) => phase)])
      .toStrictEqual([String(curriculum.BATCHES - 1), curriculum.SEGMENTS.map(() => 'agent')])
    vi.useRealTimers()
  })
})
