import type { Edition }                                from '../cards/cards.ts'
import { drawSectionCard }                             from '../cards/section-card.ts'
import { drawSiteCard }                                from '../cards/site-card.ts'
import { type Placed, type Section, SECTIONS, placed } from '../config/sections.ts'
import { badgeMarkup }                                 from '../drawing/badges.ts'
import { drawBlock }                                   from '../marks/drawings.ts'

/**
 * One way back from a missing address, the page its card leads to beside the
 * label and the line the card carries, and the section the page opens, which
 * the front page's card has none of.
 */
export interface Stop {
  label    : string
  link     : string
  note     : string
  section? : Placed
}

/**
 * The way back to the front page, where the reading starts.
 */
const FRONT: Stop = {
  label : 'The front page',
  link  : '/',
  note  : 'The story the site tells, from Blue’s bedroom to Oak’s lab.'
}

/**
 * Blue in his block, the mark the front page's card carries beside its label.
 */
const block = drawBlock()

/**
 * Draws the card a shared link to `stop`'s page shows, the site's card for the
 * front page and the section's card for a section, its edition plate naming
 * `edition`.
 */
export function cardOf(stop: Stop, edition: Edition): string {
  const { section } = stop
  return section ? drawSectionCard(edition, section, section.name) : drawSiteCard(edition)
}

/**
 * Draws the mark beside `stop`'s label, Blue in his block for the front page
 * and the section's badge in its hue for a section.
 */
export function markOf(stop: Stop): string {
  const { section } = stop
  return section ? badgeMarkup(section.badge, section.hue) : block
}

/**
 * Lists the ways back from a missing address in reading order, the front page
 * and then each of `sections` at its overview with the two lines its card
 * carries.
 */
export function stopsOf(sections: readonly Section[] = SECTIONS): Stop[] {
  return [
    FRONT,
    ...placed(sections).map(section => ({
      label   : section.name,
      link    : `/${section.folder}/`,
      note    : section.about.join(' '),
      section : section
    }))
  ]
}
