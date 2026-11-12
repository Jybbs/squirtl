import { createMarkdownRenderer } from 'vitepress'
import { describe, expect, it }   from 'vitest'

import { scrollingTables } from '../../../lib/markdown/tables.ts'

describe('scrollingTables', () => {
  it('sets each table in a block of its own and leaves the rest of the page as it renders', async () => {
    const md = await createMarkdownRenderer(process.cwd(), { config: scrollingTables })

    expect(await md.renderAsync('Before.\n\n| **A** | **B** |\n|---|---|\n| `a` | *b* |\n\nAfter.\n'))
      .toMatchInlineSnapshot(`
        "<p>Before.</p>
        <div class="table-scroll"><table>
        <thead>
        <tr>
        <th><strong>A</strong></th>
        <th><strong>B</strong></th>
        </tr>
        </thead>
        <tbody>
        <tr>
        <td><code>a</code></td>
        <td><em>b</em></td>
        </tr>
        </tbody>
        </table>
        </div>
        <p>After.</p>
        "
      `)
  })
})
