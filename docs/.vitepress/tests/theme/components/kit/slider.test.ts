// @vitest-environment happy-dom
import fs   from 'node:fs'
import path from 'node:path'

import { enableAutoUnmount, mount }            from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref }             from 'vue'

import { useBand }                               from '../../../../lib/widgets/band.ts'
import { useScrub }                              from '../../../../lib/widgets/scrub.ts'
import { OVER, type Parts, SCRUB_PARTS, Slider } from '../../../../theme/components/kit/slider.tsx'

/**
 * The folder holding the site's widgets.
 */
const COMPONENTS = path.join(import.meta.dirname, '../../../../theme/components')

/**
 * A widget naming the scrub's control or thumb, or spreading a control's or a
 * thumb's props, where only the kit's `Slider` may.
 */
const HAND_LAID = /\bscrub\.(?:control|thumb)\b|\.(?:control|thumb)\.value\b/u

vi.mock('../../../../lib/widgets/autoplay.ts', () => ({ useAutoplay: () => ({ hold: () => {} }) }))

/**
 * Mounts a slider over five positions standing at `at` around an `i` standing
 * in for a drawing, laid out by `parts` where given, and pressed through a band
 * handing the press to `pick` where given.
 */
function slid(at: number | null, parts?: Parts, pick?: (event: PointerEvent) => void) {
  return mount(defineComponent({
    setup: () => {
      const scrub = useScrub(ref(), { beat: 100, done: () => true, finish: () => {}, tick: () => {} }, {
        at       : ref(at ?? 0),
        count    : 5,
        describe : n => `Step ${n}`,
        label    : 'The episode',
        seek     : () => {}
      })
      const band  = pick ? useBand(scrub, pick) : null
      return () => h(Slider, { at, band, parts, scrub }, () => h('i'))
    }
  }), { attachTo: document.body })
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

    expect([wrapper.classes(), fill.element.style.width, wrapper.get<HTMLElement>('[role="slider"]').element.style.left])
      .toStrictEqual([['relative'], share, share])
  })

  it('lays only the control and the thumb by the classes it is given, with no bar and no position', () => {
    const wrapper = slid(null, OVER)
    const control = wrapper.get("[data-part='control']")
    const thumb   = wrapper.get<HTMLElement>('[role="slider"]')

    expect([wrapper.classes(), control.findAll('span').length, control.classes(), thumb.classes(), thumb.element.style.left])
      .toStrictEqual([
        String(OVER.root).split(' '),
        0,
        [...SCRUB_PARTS.control.split(' '), ...String(OVER.control).split(' ')],
        [...SCRUB_PARTS.thumb.split(' '), ...String(OVER.thumb).split(' ')],
        ''
      ])
  })

  it('holds the drawing it is given in its control where it draws no bar', () => {
    const control = slid(null, OVER).get("[data-part='control']")

    expect(control.findAll('*').map(part => part.element.tagName)).toStrictEqual(['I'])
  })

  it('hands a press on its control to the band, capturing the pointer and moving focus to its thumb', async () => {
    const pick    = vi.fn<(event: PointerEvent) => void>()
    const wrapper = slid(null, OVER, pick)
    const control = wrapper.get("[data-part='control']")

    await control.trigger('pointerdown', { button: 0, pointerId: 1, pointerType: 'mouse' })

    expect([pick.mock.calls.length, control.element.hasPointerCapture(1), document.activeElement])
      .toStrictEqual([1, true, wrapper.get('[role="slider"]').element])
  })
})

describe('The widgets outside the kit', () => {
  it('draw every slider through Slider, so none spreads the scrub itself', () => {
    const laid = fs.globSync('**/*.tsx', { cwd: COMPONENTS, exclude: ['kit/**'] })
      .filter(name => HAND_LAID.test(fs.readFileSync(path.join(COMPONENTS, name), 'utf8')))

    expect(laid).toStrictEqual([])
  })
})
