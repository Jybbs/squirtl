import type { ProjectFacts } from '../../lib/config/manifest.ts'

/**
 * The facts a case reads its head, its hero, and its cards from, which are the
 * facts the `pyproject.toml` a manifest case writes declares.
 */
export const FACTS: ProjectFacts = {
  base        : '/',
  description : 'Plays.',
  gate        : 95,
  homepage    : 'https://squirtl.fyi/',
  host        : 'squirtl.fyi',
  repository  : 'https://github.com/Jybbs/squirtl',
  version     : '0.2.0'
}
