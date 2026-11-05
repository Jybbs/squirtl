import { createMarkdownRenderer } from 'vitepress'
import { describe, expect, it }   from 'vitest'

import { footnotes } from '../../../lib/markdown/footnotes.ts'

const MNIH = '[^mnih2015]: Mnih et al. 2015. "Human." *Nature* 518(7540): 529–533. <https://doi.org/10.1038/nature14236>'
const PARDO = '[^pardo2018]: Pardo et al. 2018. "Time." arXiv:1. <https://arxiv.org/abs/1>'

/**
 * Renders `source` through a renderer built the way the site's configuration
 * builds it, with the bundled footnote plugin and the site's rules over it.
 */
async function rendered(source: string): Promise<string> {
  const md = await createMarkdownRenderer(process.cwd(), { config: footnotes })
  return md.renderAsync(source)
}

/**
 * Counts how many times `part` appears in `html`.
 */
function count(html: string, part: string): number {
  return html.split(part).length - 1
}

describe('the markers', () => {
  it('anchors a footnote by its key and numbers every marker of one source alike', async () => {
    const html = await rendered(`One.[^pardo2018] Two.[^mnih2015] Three.[^pardo2018]\n\n${MNIH}\n\n${PARDO}\n`)

    expect(count(html, '<a aria-label="Source 1" href="#footnote-pardo2018">')).toBe(2)
    expect(html).toContain('<a aria-label="Source 2" href="#footnote-mnih2015">')
    expect(html).toContain('id="footnote-pardo2018"')
    expect(html).toContain('id="footnote-ref-pardo2018"')
    expect(html).toContain('id="footnote-ref-pardo2018:1"')
    expect(html).not.toContain('[1:1]')
    expect(html).toContain('<a aria-label="Back to citation 2 of source 1" class="footnote-backref" href="#footnote-ref-pardo2018:1">')
  })

  it('draws a lone marker as a phone with its numeral on the glass', async () => {
    const html = await rendered(`One.[^mnih2015]\n\n${MNIH}\n`)

    expect(html).toContain('footnote-alone')
    expect(html).toContain('<span class="footnote-run">⁠<sup')
    expect(html).toContain('</sup>⁠</span>')
  })

  it('draws adjacent markers as one run, a link for each numeral around one hidden slab', async () => {
    const html = await rendered(`One.[^mnih2015][^pardo2018]\n\n${MNIH}\n\n${PARDO}\n`)
    const run  = html.slice(html.indexOf('footnote-run'), html.indexOf('</p>'))

    expect(count(run, 'footnote-run')).toBe(1)
    expect(count(run, 'class="footnote-pane"')).toBe(2)
    expect(count(run, 'class="footnote-art-phone"')).toBe(1)
    expect(count(run, 'aria-label="Source')).toBe(2)
    expect(run).toContain('footnote-first')
    expect(run).toContain('footnote-last')
    expect(run).not.toContain('footnote-alone')
  })

  it('parts markers with words between them into separate runs', async () => {
    const html = await rendered(`One.[^mnih2015] Two.[^pardo2018]\n\n${MNIH}\n\n${PARDO}\n`)

    expect(count(html, 'class="footnote-run"')).toBe(2)
  })

})

describe('the definitions', () => {
  it('splits a definition into its opener, name line, paragraph, and ways back', async () => {
    const html  = await rendered(`One.[^mnih2015] Two.[^mnih2015]\n\n${MNIH}\n`)
    const entry = html.slice(html.indexOf('<li id="footnote-mnih2015"'), html.indexOf('</li>'))

    expect(entry).toMatch(/footnote-opener[\s\S]*<strong class="footnote-name">Mnih et al\. 2015\.<\/strong>[\s\S]*<p>&quot;Human\.&quot;[\s\S]*<\/p>[\s\S]*footnote-backs/u)
    expect(count(entry.slice(entry.indexOf('footnote-backs')), 'footnote-backref')).toBe(2)
  })

  it('offers a break after each slash of an address', async () => {
    const html = await rendered(`One.[^mnih2015]\n\n${MNIH}\n`)

    expect(html).toContain('<span class="footnote-address">https://<wbr>doi.org')
    expect(html).toContain('doi.org/<wbr>10.1038/<wbr>nature14236</span>')
  })

  it('writes the name line and an address with their markup escaped, and leaves a written link as written', async () => {
    const html = await rendered('One.[^smith2020]\n\n[^smith2020]: Smith & Jones 2020. "T." [The page](https://a.example/b/c). <https://a.example/d?e=1&f=2>\n')

    expect(html).toContain('<strong class="footnote-name">Smith &amp; Jones 2020.</strong>')
    expect(html).toContain('d?e=1&amp;f=2</span>')
    expect(count(html, 'footnote-address')).toBe(1)
    expect(html).toContain('>The page</a>')
  })

  it('leaves a definition holding no year as written, under its own label', async () => {
    const html = await rendered('One.[^note] Two.^[Inline.]\n\n[^note]: A note.\n')

    expect(html).toContain('href="#footnote-note"')
    expect(html).toContain('href="#footnote-2"')
    expect(html).toContain('<p>A note.')
    expect(html).not.toContain('footnote-name')
  })

  it('holds the list on the phone, with its art hidden from the accessibility tree', async () => {
    const html = await rendered(`One.[^mnih2015]\n\n${MNIH}\n`)

    expect(html).toMatch(/<section class="footnotes footnote-snap">.*<div aria-hidden="true" class="footnote-phone-art">.*<ol class="footnotes-list">/su)
    expect(html).toContain('</ol></div></div></div></section>')
  })

  it('writes the first of several blocks of a definition with its name line', async () => {
    const html = await rendered('One.[^mnih2015]\n\n[^mnih2015]: Mnih 2015. "Human."\n\n    More.\n')

    expect(html).toContain('<strong class="footnote-name">Mnih 2015.</strong>')
    expect(html).toContain('<p>More.')
  })
})
