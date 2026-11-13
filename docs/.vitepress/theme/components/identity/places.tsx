import type { VNode } from 'vue'

import { drawSiteCard }              from '../../../lib/cards/site-card.ts'
import type { SiteTheme }            from '../../../lib/config/navigation.ts'
import { type Scheme, IDENTITY }     from '../../../lib/identity/identity.ts'
import { type Place, repositoryOf }  from '../../../lib/identity/places.ts'
import { logoLetters }               from '../../../lib/marks/logo.ts'

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
 * Draws the site's front page under its host, the name in the display face
 * with the R and the L Blue walks through in the link color, over the tagline
 * and the byline beneath it.
 */
function drawFront({ project }: SiteTheme): VNode {
  return (
    <div class="grid">
      <div class="border-b-hairline border-rule px-3 py-2 font-code text-label text-quiet">{project.host}</div>
      <div class="grid gap-2 px-3 py-4">
        <span class="font-display text-figure leading-tight font-medium text-ink">
          {Array.from(IDENTITY.name, char => <span class={logoLetters.includes(char) ? 'text-link' : undefined}>{char}</span>)}
        </span>
        <span class="font-display text-body leading-tight font-medium text-ink">{IDENTITY.tagline}</span>
        <span class="font-body text-small text-quiet">{project.description}</span>
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
  if (place === 'front') return drawFront(theme)
  return drawCard(theme, scheme)
}
