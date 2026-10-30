// @vitest-environment happy-dom
import { enableAutoUnmount, mount }        from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'

import { WalkKey } from '../../../../../theme/components/front/learning/keys.tsx'

enableAutoUnmount(afterEach)

describe('WalkKey', () => {
  it('names the strip’s marks through the key and nothing beside them', () => {
    const key = mount(WalkKey, { props: { hue: 'fern', id: 'walks' } })

    expect(key.findAll('.tracking-caps').map(name => name.text()))
      .toStrictEqual(['The coin’s presses', 'The table’s', 'Where a walk stops'])
    expect(key.text()).toBe('The coin’s pressesThe table’sWhere a walk stops')
  })
})
