import tailwindcss                 from '@tailwindcss/vite'
import vueJsx                      from '@vitejs/plugin-vue-jsx'
import type { Plugin, UserConfig } from 'vite'

import { publicDir } from './paths.ts'

/**
 * Matches each sheet the default theme imports, `vp-doc.css` among them, whose
 * `.vp-doc p` and `.vp-doc li + li` would otherwise outrank a single class.
 */
export const THEME_SHEETS = /\/vitepress\/dist\/client\/theme-default\/styles\/.+\.css$/u

/**
 * Loads the default theme's sheets into a cascade layer, so a class a widget
 * sets on an element of its own and every rule of the site's sheets outrank
 * the theme's document styles whatever their specificity.
 */
export const layerDefaultTheme = (): Plugin => ({
  enforce   : 'pre',
  name      : 'squirtl:layer-default-theme',
  transform : { filter: { id: THEME_SHEETS }, handler: layered }
})

/**
 * Wraps `code` in the `default-theme` cascade layer, beneath every rule the
 * site writes outside a layer. A layer the sheet declares itself, such as the
 * one holding the reset in `base.css`, nests inside it.
 */
export const layered = (code: string): string => `@layer default-theme {\n${code}\n}`

/**
 * Builds the Vite configuration VitePress runs its dev server and its bundler
 * under, which layers the theme's sheets beneath the site's and compiles the
 * components through Tailwind and the JSX transform.
 */
export const viteConfig = (metaUrl: string): UserConfig => ({
  css       : { transformer: 'lightningcss' },
  plugins   : [layerDefaultTheme(), tailwindcss(), vueJsx()],
  publicDir : publicDir(metaUrl)
})
