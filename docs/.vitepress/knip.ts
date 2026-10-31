import { defineConfig } from 'knip/config'

export default defineConfig({
  ignoreDependencies : ['oxlint'],
  oxlint             : { config: ['.vitepress/.oxlintrc.json'] },
  typescript         : { config: ['.vitepress/tsconfig.json'] },
  vitest             : { config: ['.vitepress/vitest.config.ts'] }
})
