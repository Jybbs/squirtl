import path from 'node:path'

import { describe, expect } from 'vitest'

import { buildNav, buildSidebar } from '../../../lib/config/navigation.ts'
import { test }                   from '../../common/checkout.ts'
import { METHODS }                from '../../common/sections.ts'

/**
 * One section a case declares.
 */
const DECLARED = [METHODS]

describe('buildNav', () => {
  test('links each section in the bar to its overview', () => {
    expect(buildNav(DECLARED))
      .toStrictEqual([{ activeMatch: '^/methods/', link: '/methods/', text: 'Methods' }])
  })
})

describe('buildSidebar', () => {
  test('lists the overview first and every other page in the order of its heading', ({ checkout }) => {
    const { root } = checkout({
      'docs/pages/methods/agent.md'  : '# The Agent\n\nText.\n',
      'docs/pages/methods/index.md'  : '# Methods\n',
      'docs/pages/methods/reward.md' : 'Lead.\n\n# A Reward\n'
    })

    expect(buildSidebar(path.join(root, 'docs', 'pages'), DECLARED)).toStrictEqual({
      '/methods/': [{
        items: [{ link: '/methods/reward', text: 'A Reward' }, { link: '/methods/agent', text: 'The Agent' }],
        link : '/methods/',
        text : 'Methods'
      }]
    })
  })

  test('fails on a page opening on no level-1 heading', ({ checkout }) => {
    const { root } = checkout({ 'docs/pages/methods/agent.md': '## Only a Second Level\n' })

    expect(() => buildSidebar(path.join(root, 'docs', 'pages'), DECLARED))
      .toThrow('opens on no level-1 heading')
  })
})
