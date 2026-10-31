// @vitest-environment happy-dom
import { describe, expect, it } from 'vitest'

import { useMotion }  from '../../../lib/widgets/motion.ts'
import { preference } from '../../common/browser.ts'

describe('useMotion', () => {
  it.each([
    ['no-preference', true],
    ['reduce', false]
  ] as const)('plays motion under %s as %s', (asked, plays) => {
    preference.value = asked

    expect(useMotion().value).toBe(plays)
  })
})
