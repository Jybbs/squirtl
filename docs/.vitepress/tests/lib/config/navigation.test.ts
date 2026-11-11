import path from 'node:path'

import { createMarkdownRenderer, disposeMdItInstance } from 'vitepress'
import { describe, expect }                           from 'vitest'

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
  test('lists the overview first and every other page by the text of its heading', async ({ checkout }) => {
    const { root } = checkout({
      'docs/pages/methods/agent.md'  : '# The Agent\n\nText.\n',
      'docs/pages/methods/cite.md'   : '# `squirtl cite`\n',
      'docs/pages/methods/index.md'  : '# Methods\n',
      'docs/pages/methods/reward.md' : 'Lead.\n\n# A Reward\n'
    })

    expect(await buildSidebar(path.join(root, 'docs', 'pages'), DECLARED)).toStrictEqual({
      '/methods/': [{
        link  : '/methods/',
        text  : 'Methods',
        items : [
          { link: '/methods/reward', text: 'A Reward' },
          { link: '/methods/cite', text: '<code>squirtl cite</code>' },
          { link: '/methods/agent', text: 'The Agent' }
        ]
      }]
    })
  })

  test('sets the markup a code span holds as text', async ({ checkout }) => {
    const { root } = checkout({ 'docs/pages/methods/run.md': '# `squirtl <command>`\n' })

    expect(await buildSidebar(path.join(root, 'docs', 'pages'), DECLARED)).toHaveProperty(
      ['/methods/', 0, 'items'],
      [{ link: '/methods/run', text: '<code>squirtl &lt;command&gt;</code>' }]
    )
  })

  test('releases the renderer, so the next caller builds its own', async ({ checkout, onTestFinished }) => {
    const { root } = checkout({ 'docs/pages/methods/agent.md': '# The Agent\n' })
    const before   = await createMarkdownRenderer(root)
    onTestFinished(disposeMdItInstance)

    await buildSidebar(path.join(root, 'docs', 'pages'), DECLARED)

    expect(await createMarkdownRenderer(root)).not.toBe(before)
  })

  test('fails on a page opening on no level-1 heading', async ({ checkout }) => {
    const { root } = checkout({ 'docs/pages/methods/agent.md': '## Only a Second Level\n' })

    await expect(buildSidebar(path.join(root, 'docs', 'pages'), DECLARED))
      .rejects.toThrow('opens on no level-1 heading')
  })
})
