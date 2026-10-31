// @vitest-environment happy-dom
import { enableAutoUnmount, mount }              from '@vue/test-utils'
import { afterEach, describe, expect, test, vi } from 'vitest'
import { defineComponent, h, ref }               from 'vue'

import type { Ticking } from '../../../lib/widgets/autoplay.ts'
import { useScrub }     from '../../../lib/widgets/scrub.ts'
import * as pointer     from '../../common/pointer.ts'

/**
 * Every hold the autoplay takes and the run each autoplay steps through, which
 * the stand-in for `useAutoplay` records.
 */
const autoplays = vi.hoisted(() => ({ holds: [] as string[], runs: [] as unknown[] }))

vi.mock('../../../lib/widgets/autoplay.ts', () => ({
  useAutoplay: (_: unknown, ticking: unknown) => {
    autoplays.runs.push(ticking)
    return { hold: (reason: string, on: boolean) => autoplays.holds.push(`${reason} ${on}`) }
  }
}))

/**
 * The run every scrubbed drawing steps through, which only its identity pins.
 */
const TICKING: Ticking = { beat: 100, done: () => true, finish: () => {}, tick: () => {} }

/**
 * Mounts a drawing ten positions wide as its own slider, recording every
 * position it seeks and every hold, and returns the wrapper beside those
 * records.
 */
function scrubbed() {
  const sought: number[] = []
  const at               = ref(3)
  autoplays.holds.length = 0
  const wrapper          = mount(defineComponent({
    setup: () => {
      const scrub = useScrub(ref(), TICKING, {
        at       : at,
        count    : 10,
        describe : n => `Step ${n}`,
        label    : 'The episode',
        seek     : n => {
          sought.push(n)
          at.value = n
        }
      })
      return () => h('div', scrub.root.value, [
        h('div', { ...scrub.control.value, class: 'control' }, [h('span', scrub.thumb.value)])
      ])
    }
  }), { attachTo: document.body })
  const control = pointer.laidOut(wrapper.get('.control'), 90, 100)
  return { at, control, holds: autoplays.holds, sought, thumb: wrapper.get('[role="slider"]'), wrapper }
}

enableAutoUnmount(afterEach)

describe('useScrub', () => {
  test('names the drawing as a slider over its positions, describing the one it shows', () => {
    const { thumb } = scrubbed()

    expect(['aria-valuemax', 'aria-valuenow', 'aria-valuetext'].map(name => thumb.attributes(name)))
      .toStrictEqual(['9', '3', 'Step 3'])
    expect(thumb.attributes('style')).toBeUndefined()
  })

  test('steps its run through the autoplay its holds reach', () => {
    autoplays.runs.length = 0
    scrubbed()

    expect(autoplays.runs).toStrictEqual([TICKING])
  })

  test('leaves off every inline style the machine sets, each part styled by its classes alone', () => {
    const { wrapper } = scrubbed()
    const styles      = wrapper.findAll('div, span').map(part => part.attributes('style'))

    expect(styles).toStrictEqual([undefined, undefined, undefined])
  })
})

describe('useScrub under a pointer and the keys', () => {
  test('holds the position under a mouse crossing the drawing, and the autoplay while it rests', async () => {
    const { control, holds, sought } = scrubbed()

    await pointer.sweep(control, [150])
    await control.trigger('pointerleave', { pointerType: 'mouse' })

    expect([sought, holds]).toStrictEqual([[], ['pointer true', 'pointer false']])
  })

  test('seeks the position a press along the drawing lands on', async () => {
    const { control, sought } = scrubbed()

    await pointer.press(control, 150)

    expect(sought).toStrictEqual([5])
  })

  test('leaves the autoplay running under a touch, which holds nothing until it presses', async () => {
    const { control, holds, sought } = scrubbed()

    await control.trigger('pointerenter', { pointerType: 'touch' })
    await control.trigger('pointermove', { clientX: 150, pointerType: 'touch' })

    expect([sought, holds]).toStrictEqual([[], []])
  })

  test('steps a position with the arrow keys once the thumb has focus, holding the autoplay', async () => {
    const { holds, sought, thumb } = scrubbed()

    await thumb.trigger('focusin')
    await thumb.trigger('keydown', { key: 'ArrowRight' })

    expect([sought, holds[0]]).toStrictEqual([[4], 'keys true'])
  })
})
