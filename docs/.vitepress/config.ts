import tailwindcss               from '@tailwindcss/vite'
import vueJsx                    from '@vitejs/plugin-vue-jsx'
import { defineConfigWithTheme } from 'vitepress'

import { siteHead }      from './lib/config/head.ts'
import { pageHooks }     from './lib/config/hooks.ts'
import { projectFacts }  from './lib/config/manifest.ts'
import * as navigation   from './lib/config/navigation.ts'
import * as paths        from './lib/config/paths.ts'
import { IDENTITY }      from './lib/identity/identity.ts'
import { markdownRules } from './lib/markdown/rules.ts'

const facts = projectFacts(import.meta.url)
const pages = paths.pagesDir(import.meta.url)

export default defineConfigWithTheme<navigation.SiteTheme>({
  ...pageHooks(facts, import.meta.url),
  base        : facts.base,
  cacheDir    : paths.cacheDir(import.meta.url, 'vitepress'),
  cleanUrls   : true,
  description : facts.description,
  head        : siteHead(facts),
  lang        : 'en-US',
  markdown    : { config: markdownRules, math: true },
  sitemap     : { hostname: facts.homepage },
  srcDir      : pages,
  title       : IDENTITY.name,

  themeConfig: {
    edition   : { host: facts.host, version: facts.version },
    logo      : { alt: IDENTITY.name, dark: '/mark-dark.svg', light: '/mark-light.svg' },
    nav       : navigation.buildNav(),
    sidebar   : navigation.buildSidebar(pages),
    siteTitle : false
  },

  vite: {
    css       : { transformer: 'lightningcss' },
    plugins   : [tailwindcss(), vueJsx()],
    publicDir : paths.publicDir(import.meta.url)
  }
})
