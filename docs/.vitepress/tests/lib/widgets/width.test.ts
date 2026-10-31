// @vitest-environment happy-dom
import { enableAutoUnmount, mount }                  from '@vue/test-utils'
import { afterEach, describe, expect, it }           from 'vitest'
import { type ComputedRef, defineComponent, h, ref } from 'vue'

import { IDENTITY }      from '../../../lib/identity/identity.ts'
import { useDrawnWidth } from '../../../lib/widgets/width.ts'

/**
 * Mounts a widget whose drawing is not yet laid out, measured no narrower than
 * `least`, and returns its width.
 */
function drawnWidth(least: number): ComputedRef<number> {
  let width!: ComputedRef<number>
  mount(defineComponent({
    setup: () => {
      width = useDrawnWidth(ref<HTMLElement>(), least)
      return () => h('div')
    }
  }))
  return width
}

enableAutoUnmount(afterEach)

describe('useDrawnWidth', () => {
  it.each([
    ['a plate', 240, IDENTITY.lengths.plate],
    ['the least', IDENTITY.lengths.plate + 100, IDENTITY.lengths.plate + 100]
  ])('reads %s before the drawing is measured', (_, least, width) => {
    expect(drawnWidth(least).value).toBe(width)
  })
})
