// @vitest-environment happy-dom
import { enableAutoUnmount, mount }            from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ref }                                 from 'vue'

import { METHODS } from '../../../common/sections.ts'

/**
 * The page a case shows, under the one section the site carries in it.
 */
const page = ref({ isNotFound: false, relativePath: 'methods/reward.md' })

vi.mock('vitepress', () => ({ useData: () => ({ page }) }))
vi.mock('../../../../lib/config/sections.ts', async original => {
  const sections = await original<typeof import('../../../../lib/config/sections.ts')>()
  return { ...sections, sectionOf: (shown: typeof page.value) => sections.sectionOf(shown, [METHODS]) }
})

const { SectionMark } = await import('../../../../theme/components/section/ribbon.tsx')

enableAutoUnmount(afterEach)

describe('SectionMark', () => {
  it('hangs a ribbon in the section’s hue with its badge at the tail, and names it in a chip', () => {
    page.value  = { isNotFound: false, relativePath: 'methods/reward.md' }
    const marks = mount(SectionMark)

    expect(marks.get('.section-ribbon').classes()).toContain('bg-indigo-badge-2')
    expect(marks.get('.section-badge').classes()).toContain('bg-indigo-1')
    expect(marks.get('.section-badge svg').html()).toContain('var(--color-indigo-badge-')
    expect(marks.get('.tracking-caps').text()).toBe('Methods')
  })

  it.each([
    [{ isNotFound: false, relativePath: 'index.md' }],
    [{ isNotFound: true, relativePath: 'methods/missing.md' }]
  ])('marks nothing on a page no section holds, such as %j', shown => {
    page.value = shown

    expect(mount(SectionMark).find('.section-mark').exists()).toBe(false)
  })
})
