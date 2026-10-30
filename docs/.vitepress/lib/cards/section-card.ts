import KANTO            from '../art/kanto.json' with { type: 'json' }
import { type Placed, SECTIONS, type Section, placed } from '../config/sections.ts'
import { dotText }      from '../drawing/dots.ts'
import { spriteMarkup } from '../drawing/sprites.ts'
import * as identity    from '../identity/identity.ts'
import * as cards       from './cards.ts'

/**
 * The steps of one hue's ramp on the dark ground, beside the color the hue marks
 * in there.
 */
type Ramp = (typeof identity.IDENTITY.hues)[identity.Hue]['dark'] & { hue: string }

/**
 * How a section card sets its words, the section's crumb opening the column,
 * the page's title in dots of at most `most` pixels to a cell, its top `title`
 * below the crumb's baseline, and the section's two lines about itself, the
 * first `drop` below the crumb's baseline once the title's height is added.
 */
const COLUMN = {
  about : { drop: 92, lead: 38, size: 25 },
  crumb : { gap: 48, height: 3, rise: 7, size: 26, width: 34 },
  most  : 9,
  title : 40
}

/**
 * How a section card draws the Kanto map, its left and top, the card's pixels
 * to one of the map's, the opacity it is faded to, and the left edge of the
 * room it takes from the words, beside how the cities and the badge are marked
 * on it.
 */
const MAP = {
  city  : { corner: 4, faint: 0.6, side: 18, stroke: 3 },
  fade  : 0.75,
  left  : 610,
  ring  : { dot: 6, radius: 22, stroke: 4 },
  room  : 600,
  scale : 3.5,
  top   : 63,
  badge : {
    bounds : { bottom: 560, left: 620, right: 1150, top: 88 },
    box    : { corner: 28, pad: 16, stroke: 3 },
    gap    : 44,
    lead   : { dash: '3 6', width: 2 },
    pixel  : 9
  }
}

/**
 * How a section card marks the sections on the edition plate's line, one dot to
 * a section, `gap` apart and ending at `right`, the section's own dot the
 * larger.
 */
const PAGES = { gap: 22, other: 4, own: 7, right: 1128 }

/**
 * Reads the steps of `hue`'s ramp on the dark ground beside the color the hue
 * marks in there, as the site's theme writes it.
 */
function badgeRampOf(hue: identity.Hue): Ramp {
  return { ...identity.IDENTITY.hues[hue].dark, hue: identity.IDENTITY.marks[hue].dark }
}

/**
 * Finds the center of the city of the gym whose badge `section` carries, on the
 * Kanto map drawn where `MAP` places it.
 */
function cityOf(section: Placed): cards.Point {
  const tile        = (KANTO.cities as Readonly<Record<string, readonly number[]>>)[section.badge.name]!
  const [x, y]      = tile as [number, number]
  const [left, top] = KANTO.origin as [number, number]
  const square      = KANTO.tile * MAP.scale
  return { x: MAP.left + (x + left + 0.5) * square, y: MAP.top + (y + top + 0.5) * square }
}

/**
 * Holds `value` between `low` and `high`.
 */
const clamp = (value: number, low: number, high: number): number => Math.min(high, Math.max(low, value))

/**
 * Draws the Kanto map faded in `section`'s hue, with the city of every other
 * section in `all` marked faintly in that section's hue.
 */
function kantoMap(all: readonly Placed[], section: Placed): string {
  const { city, fade, left, scale, top } = MAP
  const { ground, lift }                 = identity.IDENTITY.tones.dark

  const tones = badgeRampOf(section.hue)
  const id    = `faded-${section.hue}`
  const marks = all.filter(each => each.index !== section.index).map(each => {
    const point = cityOf(each)
    return `<rect x="${point.x - city.side / 2}" y="${point.y - city.side / 2}" width="${city.side}" `
         + `height="${city.side}" rx="${city.corner}" fill="none" stroke="${badgeRampOf(each.hue).hue}" `
         + `stroke-width="${city.stroke}" opacity="${city.faint}"/>`
  })

  return `<defs>${rampFilter([tones.shades[1]!, tones.shades[0]!, lift, ground], id)}</defs>`
       + `<image href="${KANTO.image}" x="${left}" y="${top}" width="${KANTO.width * scale}" `
       + `height="${KANTO.height * scale}" filter="url(#${id})" opacity="${fade}" `
       + 'image-rendering="optimizeSpeed" preserveAspectRatio="none"/>'
       + marks.join('')
}

/**
 * Marks each section in `all` with a dot on the edition plate's line, the dot
 * of `section` the larger and at full strength.
 */
function pageDots(all: readonly Placed[], section: Placed): string {
  return all
    .map((each, i) => {
      const mine = each.index === section.index
      return `<circle cx="${PAGES.right - (all.length - 1 - i) * PAGES.gap}" cy="${cards.plateLine}" `
           + `r="${mine ? PAGES.own : PAGES.other}" fill="${badgeRampOf(each.hue).hue}" `
           + `opacity="${mine ? 1 : MAP.city.faint}"/>`
    })
    .join('')
}

/**
 * Writes a filter mapping the four grays of the Kanto map, from the darkest to
 * the lightest, onto `colors`, one discrete step to a gray in each channel.
 */
function rampFilter(colors: readonly string[], id: string): string {
  const channel = (offset: number): string => colors
    .map(hex => (identity.rgbOf(hex)[offset]! / 255).toFixed(4))
    .join(' ')

  return `<filter id="${id}" color-interpolation-filters="sRGB"><feComponentTransfer>`
       + `<feFuncR type="discrete" tableValues="${channel(0)}"/>`
       + `<feFuncG type="discrete" tableValues="${channel(1)}"/>`
       + `<feFuncB type="discrete" tableValues="${channel(2)}"/></feComponentTransfer></filter>`
}

/**
 * Rings the city of `section`'s badge and sets the badge in a box above the
 * city, or below it where the box would rise past its bounds, joined to the
 * ring by a dashed line.
 */
function ringedBadge(section: Placed): string {
  const { badge: { bounds, box, gap, lead, pixel }, ring } = MAP
  const tones = badgeRampOf(section.hue)
  const own   = cityOf(section)
  const span  = section.badge.grid.length * pixel
  const x     = clamp(own.x - span / 2, bounds.left, bounds.right - span)
  const above = own.y - span - gap
  const y     = above >= bounds.top ? above : clamp(own.y + gap, bounds.top, bounds.bottom - span)
  const below = y > own.y
  const side  = span + 2 * box.pad
  const fills = [tones.shades[1]!, tones.shades[2]!, tones.hue, tones.pale]

  return `<circle cx="${own.x}" cy="${own.y}" r="${ring.radius}" fill="none" stroke="${tones.pale}" `
       + `stroke-width="${ring.stroke}"/>`
       + `<circle cx="${own.x}" cy="${own.y}" r="${ring.dot}" fill="${tones.pale}"/>`
       + `<line x1="${own.x}" y1="${own.y + (below ? ring.radius : -ring.radius)}" x2="${x + span / 2}" `
       + `y2="${below ? y - box.pad : y + span + box.pad}" stroke="${tones.pale}" `
       + `stroke-width="${lead.width}" stroke-dasharray="${lead.dash}"/>`
       + `<rect x="${x - box.pad}" y="${y - box.pad}" width="${side}" height="${side}" rx="${box.corner}" `
       + `fill="${identity.IDENTITY.tones.dark.ground}" stroke="${tones.hue}" stroke-width="${box.stroke}"/>`
       + spriteMarkup(section.badge.grid, { fills, size: pixel, x, y })
}

/**
 * Draws a section card's column of words, the section's crumb counting it among
 * `count` sections, the page's title in dots, the section's lines about itself,
 * and the edition plate.
 */
function sectionColumn(count: number, facts: cards.Edition, section: Placed, title: string): string {
  const { about, crumb, most, title: drop } = COLUMN
  const { gap, inset, top }                 = cards.MARGIN
  const { ink, quiet }                      = identity.IDENTITY.tones.dark
  const { text }                            = badgeRampOf(section.hue)

  const cell  = cards.fitCell(title, most, MAP.room - inset - gap)
  const first = top + about.drop + cards.CAPITAL * cell
  const lines = section.about.map((words, i) =>
    cards.setLine(words, { fill: quiet, size: about.size, x: inset, y: first + i * about.lead }))

  return `<rect x="${inset}" y="${top - crumb.rise}" width="${crumb.width}" height="${crumb.height}" `
       + `fill="${text}"/>`
       + cards.setCaps(`${section.name} · Section ${section.index + 1} of ${count}`,
                       { fill: text, size: crumb.size, x: inset + crumb.gap, y: top })
       + dotText(title, { cell, fill: ink, x: inset, y: top + drop + cards.CAPITAL * cell })
       + lines.join('')
       + cards.drawPlate(facts, 'dark')
}

/**
 * Draws the card a link to a page of `section` shows, the Kanto map faded in
 * the section's hue with the city of its badge ringed and the badge set beside
 * it, every other section's city marked faintly, and a column of words naming
 * the section and the page's `title`.
 *
 * Args:
 *   facts    : The version and the host the edition plate names.
 *   section  : The section holding the page, whose place sets the card's hue
 *     and its badge.
 *   title    : The page's title.
 *   sections : The sections the site carries, which the card counts and marks.
 */
export function drawSectionCard(
  facts    : cards.Edition,
  section  : Placed,
  title    : string,
  sections : readonly Section[] = SECTIONS
): string {
  const all = placed(sections)
  const art = kantoMap(all, section) + ringedBadge(section) + pageDots(all, section)
  return cards.wrapCard(art + sectionColumn(all.length, facts, section, title), 'dark')
}
