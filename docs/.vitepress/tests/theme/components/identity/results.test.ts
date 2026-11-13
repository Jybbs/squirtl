// @vitest-environment happy-dom
import { mount }                from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import { SAMPLE, lookOf } from '../../../../lib/results/legend.ts'

const { IdentityResults } = await import('../../../../theme/components/identity/results.tsx')

describe('IdentityResults', () => {
  it('heads a row for each part the Results charts draw, on the made-up groups', () => {
    const wrapper = mount(IdentityResults)

    expect(wrapper.findAll('.results-legend > span').map(head => head.text()))
      .toStrictEqual(lookOf(SAMPLE.groups, SAMPLE.random, 'hatch').map(row => row.head))
    expect(wrapper.text()).toBePublishedProse()
  })
})
