// @vitest-environment happy-dom
import { enableAutoUnmount, mount }            from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref }             from 'vue'

import { useScrub }           from '../../../../lib/widgets/scrub.ts'
import { type Parts, Slider } from '../../../../theme/components/kit/slider.tsx'
import { OVER, SCRUB_PARTS }  from '../../../../theme/components/kit/widget.ts'

vi.mock('../../../../lib/widgets/autoplay.ts', () => ({ useAutoplay: () => ({ hold: () => {} }) }))

/**
 * Mounts a slider over five positions standing at `at`, laid out by `parts`
 * where given.
 */
function slid(at: number | null, parts?: Parts) {
  return mount(defineComponent({
    setup: () => {
      const scrub = useScrub(ref(), { beat: 100, done: () => true, finish: () => {}, tick: () => {} }, {
        at       : ref(at ?? 0),
        count    : 5,
        describe : n => `Step ${n}`,
        label    : 'The episode',
        seek     : () => {}
      })
      return () => h(Slider, { at, parts, scrub })
    }
  }))
}

enableAutoUnmount(afterEach)

describe('Slider', () => {
  it.each([
    { at: 0, share: '0%' },
    { at: 2, share: '50%' },
    { at: 4, share: '100%' },
    { at: 5, share: '100%' },
    { at: -1, share: '0%' }
  ])('stands the fill and the thumb at $share of the bar at position $at of five', ({ at, share }) => {
    const wrapper = slid(at)
    const fill    = wrapper.get<HTMLElement>("[data-part='control'] span:last-child")

    expect([fill.element.style.width, wrapper.get<HTMLElement>('[role="slider"]').element.style.left])
      .toStrictEqual([share, share])
  })

  it('lays only the control and the thumb by the classes it is given, with no bar and no position', () => {
    const wrapper = slid(null, OVER)
    const control = wrapper.get("[data-part='control']")
    const thumb   = wrapper.get<HTMLElement>('[role="slider"]')

    expect([control.findAll('span').length, control.classes(), thumb.classes(), thumb.element.style.left])
      .toStrictEqual([
        0,
        [...SCRUB_PARTS.control.split(' '), ...String(OVER.control).split(' ')],
        [...SCRUB_PARTS.thumb.split(' '), ...String(OVER.thumb).split(' ')],
        ''
      ])
  })
})
