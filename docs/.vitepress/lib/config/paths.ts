import fs                from 'node:fs'
import path              from 'node:path'
import { fileURLToPath } from 'node:url'

/**
 * Finds the folder under `.cache/` at the root of the checkout that the tool
 * `name` names keeps its cache in.
 */
export const cacheDir = (metaUrl: string, name: string): string =>
  path.join(repoRoot(metaUrl), '.cache', name)

/**
 * Finds the site's own folder, `docs/` at the root of the checkout.
 */
export const docsDir = (metaUrl: string): string => path.join(repoRoot(metaUrl), 'docs')

/**
 * Finds the folder every page sits under, which the configuration names as
 * VitePress's `srcDir`.
 */
export const pagesDir = (metaUrl: string): string => path.join(docsDir(metaUrl), 'pages')

/**
 * Finds the folder whose files VitePress copies to the root of the deployment
 * under their own names.
 */
export const publicDir = (metaUrl: string): string => path.join(docsDir(metaUrl), 'public')

/**
 * Finds the root of the checkout holding the module at `metaUrl`, the first
 * folder above it that holds `.git`, which a worktree carries as a file and a
 * clone as a folder.
 */
export function repoRoot(metaUrl: string): string {
  let directory = path.dirname(fileURLToPath(metaUrl))
  while (!fs.existsSync(path.join(directory, '.git'))) {
    const parent = path.dirname(directory)
    if (parent === directory) throw new Error(`No checkout holds ${metaUrl}`)
    directory = parent
  }
  return directory
}
