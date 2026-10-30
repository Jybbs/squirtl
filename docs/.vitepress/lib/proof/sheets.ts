import fs   from 'node:fs'
import path from 'node:path'

import { compile } from '@tailwindcss/node'
import { Scanner } from '@tailwindcss/oxide'

import { docsDir }  from '../config/paths.ts'
import { literals } from './literals.ts'

/**
 * One stylesheet the site's CSS is built from, under the name a finding reports
 * it by.
 */
export interface Sheet {
  css  : string
  name : string
}

/**
 * Reads every stylesheet the theme builds its CSS from, meaning the utilities
 * Tailwind builds from the theme's sheet for the classes the components carry,
 * and each other sheet under `theme/styles/`.
 */
export async function siteSheets(metaUrl: string): Promise<Sheet[]> {
  const styles   = path.join(docsDir(metaUrl), '.vitepress', 'theme', 'styles')
  const entry    = fs.readFileSync(path.join(styles, 'site.css'), 'utf8')
  const compiler = await compile(entry, { base: styles, onDependency: () => {} })
  const scanner  = new Scanner({ sources: compiler.sources })
  const others   = fs.globSync('**/*.css', { cwd: styles, exclude: ['site.css'] })
    .toSorted()
    .map(file => ({ css: fs.readFileSync(path.join(styles, file), 'utf8'), name: `theme/styles/${file}` }))

  return [{ css: compiler.build(scanner.scan()), name: 'the utilities' }, ...others]
}

/**
 * Prints each literal `sheets` set that no theme variable supplies, beside the
 * sheet it sits in.
 *
 * Returns:
 *   The exit status, 1 where any sheet sets such a literal and 0 otherwise.
 */
export function prove(sheets: readonly Sheet[]): number {
  const found = sheets.flatMap(({ css, name }) =>
    literals(css).map(declaration => `${name} sets ${declaration}`))
  for (const each of found) console.error(`${each}, which no theme variable supplies`)
  return found.length > 0 ? 1 : 0
}
