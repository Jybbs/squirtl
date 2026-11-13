// @vitest-environment happy-dom
import { enableAutoUnmount, mount }        from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { defineComponent, ref }            from 'vue'

import { useComparison } from '../../../lib/results/fold.ts'
import * as results      from '../../../lib/results/results.ts'
import FIXTURE           from './fixtures/results.json' with { type: 'json' }

enableAutoUnmount(afterEach)

describe('useComparison', () => {
  it('draws the runs it is handed in place of the committed ones', () => {
    const handed = FIXTURE as unknown as results.Results
    let drawn: readonly results.Group[] = []
    mount(defineComponent({ setup: () => { drawn = useComparison(ref(), 'hatch', handed).groups; return () => null } }))

    expect(drawn).toStrictEqual(results.groupsOf(handed))
  })
})
