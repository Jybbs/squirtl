// @vitest-environment happy-dom
import { describe, expect, it } from 'vitest'

import { still } from '../../../lib/widgets/still.ts'

describe('still', () => {
  it('sets the styles with every transition off, then turns the transitions back on', () => {
    const nodes = [document.createElement('span'), document.createElement('span')]
    let during  = ['', '']

    still(nodes, () => {
      nodes[0]!.style.width = '10px'
      during = nodes.map(node => node.style.transition)
    })

    expect([during, nodes.map(node => node.style.transition), nodes[0]!.style.width]).toStrictEqual([['none', 'none'], ['', ''], '10px'])
  })

  it('runs over no nodes', () => {
    let ran = false
    still([], () => { ran = true })

    expect(ran).toBe(true)
  })
})
