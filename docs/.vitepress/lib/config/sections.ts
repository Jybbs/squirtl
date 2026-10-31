import type { PageData } from 'vitepress'

import * as identity from '../identity/identity.ts'

/**
 * A section beside the folder its one word names, the hue the identity gives
 * that folder, and the gym badge its place among the sections gives it.
 */
export interface Placed extends Section {
  badge  : identity.Badge
  folder : identity.Folder
  hue    : identity.Hue
  index  : number
}

/**
 * One section of the site, a folder under `docs/pages/` that opens on an
 * `index.md` overview, named by the one word that serves as its folder, its
 * label in the navigation bar, and its heading.
 */
export interface Section {
  about : readonly [string, string]
  name  : Capitalize<identity.Folder>
}

/**
 * The sections the site carries, in alphabetical order of their names.
 */
export const SECTIONS: readonly Section[] = []

/**
 * Places each of `sections`, giving each the hue the identity declares for its
 * folder, the first the first badge the game awards, and each later section the
 * badge after its predecessor's.
 */
export function placed(sections: readonly Section[] = SECTIONS): Placed[] {
  return sections.map((section, index) => {
    const folder = section.name.toLowerCase() as identity.Folder

    return {
      ...section,
      badge  : identity.IDENTITY.badges[index % identity.IDENTITY.badges.length]!,
      folder : folder,
      hue    : identity.sectionHue(folder),
      index  : index
    }
  })
}

/**
 * Finds the section holding `page` by the folder under `docs/pages/` it sits
 * in, or `undefined` for a page no section holds and for the page a reader
 * meets at a missing address.
 */
export function sectionOf(
  page     : Pick<PageData, 'isNotFound' | 'relativePath'>,
  sections : readonly Section[] = SECTIONS
): Placed | undefined {
  if (page.isNotFound) return undefined
  const folder = page.relativePath.split('/', 1)[0]
  return placed(sections).find(section => section.folder === folder)
}
