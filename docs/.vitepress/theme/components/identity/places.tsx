import type { VNode } from 'vue'

import coverage from '../../../../assets/badges/coverage.svg'
import docs     from '../../../../assets/badges/docs.svg'
import python   from '../../../../assets/badges/python.svg'

import { drawSiteCard }                from '../../../lib/cards/site-card.ts'
import type { SiteTheme }              from '../../../lib/config/navigation.ts'
import { type Scheme, IDENTITY }       from '../../../lib/identity/identity.ts'
import { type Place, badgesOf, repositoryOf } from '../../../lib/identity/places.ts'
import { drawLogo }                    from '../../../lib/marks/drawings.ts'

/**
 * The icon each badge of the README draws beside its value, by the name it
 * stands for.
 */
const ICONS: Readonly<Record<string, string>> = { Coverage: coverage, Docs: docs, Python: python }

/**
 * The tabs GitHub's repository page sets above its files, the first open.
 */
const TABS = ['Code', 'Issues', 'Pull requests', 'Actions']

/**
 * Draws GitHub's repository page, the byline in its About box beside the
 * site's host and the keywords.
 */
function drawGithub({ project }: SiteTheme): VNode {
  const repo = repositoryOf(project.repository)

  return (
    <div class="grid text-small">
      <div class="flex flex-wrap items-center gap-2 px-3 pt-3 pb-2">
        <span class="text-body text-link">{repo.owner} / <strong>{repo.name}</strong></span>
        <span class="rounded-full border-hairline border-rule px-2 font-code text-label text-quiet">Public</span>
      </div>
      <div aria-hidden="true" class="flex gap-3 overflow-hidden border-b-hairline border-rule px-3 whitespace-nowrap">
        {TABS.map((tab, n) => <span class="identity-gh-tab pt-1 pb-2 text-quiet" data-on={n === 0}>{tab}</span>)}
      </div>
      <aside class="grid content-start gap-2 p-3">
        <div class="font-semibold">About</div>
        <div class="font-body text-small">{project.description}</div>
        <div class="font-semibold text-link">{project.host}</div>
        <div class="flex flex-wrap gap-1">
          {project.keywords.map(word => <span class="identity-topic rounded-full px-2 font-code text-label text-link">{word}</span>)}
        </div>
      </aside>
    </div>
  )
}

/**
 * Draws the README as GitHub shows it, the logo on `scheme`'s ground over the
 * tagline in italics and the badges.
 */
function drawReadme({ project }: SiteTheme, scheme: Scheme): VNode {
  return (
    <div class="grid">
      <div aria-hidden="true" class="flex gap-3 border-b-hairline border-rule px-3 pt-2 text-small">
        <span class="identity-gh-tab pb-2" data-on="true">README</span>
        <span class="pb-2 text-quiet">MIT license</span>
      </div>
      <div class="grid justify-items-center gap-3 px-3 py-4 text-center">
        <span class="identity-readme-mark block w-full" innerHTML={drawLogo(scheme)} />
        <div class="font-body text-body italic">{IDENTITY.tagline}</div>
        <div class="flex flex-wrap justify-center gap-1">
          {badgesOf(project).map(badge => (
            <span class="inline-flex">
              <img alt={badge.name} class="identity-badge block" src={ICONS[badge.name]} />
              <span class="flex items-center bg-primary px-2 font-code text-label font-bold tracking-caps text-athens-gray uppercase">{badge.value}</span>
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

/**
 * Draws a link to the site as a chat unfurls it, the host, the name, and the
 * byline over the site's card on `scheme`'s ground.
 */
function drawCard({ edition, project }: SiteTheme, scheme: Scheme): VNode {
  return (
    <div class="grid gap-0 border-l-bar border-rule p-3">
      <span class="font-code text-label text-quiet">{project.host}</span>
      <span class="text-body font-semibold text-link">{IDENTITY.name}</span>
      <span class="mb-2 font-body text-small">{project.description}</span>
      <span class="identity-card-art block overflow-hidden rounded-2" innerHTML={drawSiteCard(edition, scheme)} />
    </div>
  )
}

/**
 * Draws `place` as the theme's facts and `scheme`'s ground set it.
 */
export function drawPlace(place: Place, theme: SiteTheme, scheme: Scheme): VNode {
  if (place === 'github') return drawGithub(theme)
  if (place === 'readme') return drawReadme(theme, scheme)
  return drawCard(theme, scheme)
}
