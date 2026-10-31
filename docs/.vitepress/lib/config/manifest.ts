import fs   from 'node:fs'
import path from 'node:path'

import { parse } from 'smol-toml'

import { repoRoot } from './paths.ts'

/**
 * The type a manifest value of each kind `required` reads takes.
 */
interface Kinds {
  number : number
  string : string
}

/**
 * What the site states about the project, read from `pyproject.toml`.
 */
export interface ProjectFacts {
  base        : string
  description : string
  gate        : number
  homepage    : string
  host        : string
  repository  : string
  version     : string
}

/**
 * One table of the parsed manifest, its keys beside their values.
 */
type Table = Record<string, unknown>

/**
 * Reads the value `keys` leads to through the parsed manifest, failing by the
 * dotted name of the key where the value is missing or of another type than
 * `kind`.
 */
function required<K extends keyof Kinds>(manifest: unknown, kind: K, ...keys: string[]): Kinds[K] {
  const value = keys.reduce<unknown>((table, key) => (table as Table | undefined)?.[key], manifest)
  if (typeof value !== kind || value === '') throw new Error(`pyproject.toml declares no ${keys.join('.')}`)
  return value as Kinds[K]
}

/**
 * Reads what the site states about the project out of the `pyproject.toml` at
 * the root of the checkout holding `metaUrl`, the base path the site serves
 * under being the path of `[project.urls].Homepage` and the host the host of
 * that address, beside the description, the repository's address, the version,
 * and the coverage `[tool.coverage.report].fail_under` holds the package's
 * suite to, which the site's suite takes as well.
 */
export function projectFacts(metaUrl: string): ProjectFacts {
  const manifest = parse(fs.readFileSync(path.join(repoRoot(metaUrl), 'pyproject.toml'), 'utf8'))
  const homepage = required(manifest, 'string', 'project', 'urls', 'Homepage')
  if (!homepage.endsWith('/')) {
    throw new Error('pyproject.toml declares a project.urls.Homepage with no closing slash')
  }
  const { host, pathname } = new URL(homepage)

  return {
    base        : pathname,
    description : required(manifest, 'string', 'project', 'description'),
    gate        : required(manifest, 'number', 'tool', 'coverage', 'report', 'fail_under'),
    homepage    : homepage,
    host        : host,
    repository  : required(manifest, 'string', 'project', 'urls', 'Repository'),
    version     : required(manifest, 'string', 'project', 'version')
  }
}
