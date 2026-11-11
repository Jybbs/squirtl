import fs                       from 'node:fs'
import { fileURLToPath }        from 'node:url'
import type { Plugin }          from 'vite'
import { describe, expect, it } from 'vitest'

import * as paths from '../../../lib/config/paths.ts'
import * as vite  from '../../../lib/config/vite.ts'

/**
 * The folder the default theme's sheets sit in once the site's packages are
 * installed.
 */
const STYLES = '/docs/node_modules/vitepress/dist/client/theme-default/styles'

describe('THEME_SHEETS', () => {
  it.each([
    `${STYLES}/base.css`,
    `${STYLES}/vars.css`,
    `${STYLES}/components/vp-doc.css`
  ])('matches the default theme sheet %s', id => {
    expect(vite.THEME_SHEETS.test(id)).toBe(true)
  })

  it('matches every sheet the installed default theme imports', () => {
    const entry  = new URL(import.meta.resolve('vitepress/theme-without-fonts'))
    const sheets = [...fs.readFileSync(entry, 'utf8').matchAll(/^import "(\.\/styles\/.+\.css)"/gmu)]
      .map(([, sheet]) => fileURLToPath(new URL(sheet!, entry)))
    expect(sheets).toContainEqual(expect.stringMatching(/vp-doc\.css$/u))
    expect(sheets.filter(sheet => !vite.THEME_SHEETS.test(sheet))).toEqual([])
  })

  it.each([
    '/docs/.vitepress/theme/styles/site.css',
    '/docs/.vitepress/theme/styles/methods/memory.css',
    '/docs/node_modules/vitepress/dist/client/theme-default/components/VPDoc.vue',
    `${STYLES}/components/vp-doc.css.map`
  ])('leaves %s out', id => {
    expect(vite.THEME_SHEETS.test(id)).toBe(false)
  })
})

describe('layered', () => {
  it('wraps a sheet in the theme layer', () => {
    expect(vite.layered('.vp-doc p { margin: 1rem 0; }'))
      .toBe('@layer default-theme {\n.vp-doc p { margin: 1rem 0; }\n}')
  })

  it('nests a layer the sheet declares inside the theme layer', () => {
    expect(vite.layered('@layer __vitepress_base { p { margin: 0; } }'))
      .toBe('@layer default-theme {\n@layer __vitepress_base { p { margin: 0; } }\n}')
  })
})

describe('layerDefaultTheme', () => {
  const plugin = vite.layerDefaultTheme()

  it('runs before the plugins that compile a sheet', () => {
    expect(plugin.enforce).toBe('pre')
  })

  it('filters on the default theme sheets and wraps each one', () => {
    const transform = plugin.transform as { filter: { id: RegExp }, handler: (code: string) => string }
    expect(transform.filter.id).toBe(vite.THEME_SHEETS)
    expect(transform.handler('a { color: inherit; }')).toBe(vite.layered('a { color: inherit; }'))
  })
})

describe('viteConfig', () => {
  const metaUrl = import.meta.url
  const config  = vite.viteConfig(metaUrl)

  it('layers the default theme before Tailwind and the JSX transform', () => {
    const names = (config.plugins!.flat() as Plugin[]).map(plugin => plugin.name)
    expect(names[0]).toBe(vite.layerDefaultTheme().name)
    expect(names.slice(1).some(name => name.startsWith('@tailwindcss/vite'))).toBe(true)
    expect(names).toContain('vite:vue-jsx')
  })

  it('compiles the sheets through Lightning CSS', () => {
    expect(config.css).toEqual({ transformer: 'lightningcss' })
  })

  it('copies the public folder to the root of the deployment', () => {
    expect(config.publicDir).toBe(paths.publicDir(metaUrl))
  })
})
