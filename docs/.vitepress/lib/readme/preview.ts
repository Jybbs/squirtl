import fs   from 'node:fs'
import path from 'node:path'

import { docsDir }                from '../config/paths.ts'
import { type Moment, walksOf }   from '../front/learning.ts'
import type { Scheme }            from '../identity/identity.ts'
import { SCHEMES }                from '../identity/palette.ts'
import { count, counted, listed } from '../widgets/numbers.ts'
import { encodeGif }              from './gif.ts'
import * as movie                 from './movie.ts'

/**
 * Counts the presses of `moment` as a sentence names them.
 */
function pressesOf(moment: Moment): string {
  return counted(moment.presses, 'press', 'presses')
}

/**
 * Describes the preview in one sentence for its alt text, from the walks
 * `moments` hold.
 */
export function previewAlt(moments: readonly Moment[] = walksOf()): string {
  const [last, first] = [moments.at(-1)!, moments[0]!]
  return `Blue walks from his door in Pallet Town to its north edge with the table as it stood after `
       + `${listed(moments.map(moment => moment.episodes))} episodes of training, every walk on one clock, `
       + `the walk after ${count(last.episodes)} episodes arriving in ${pressesOf(last)} and the walk after `
       + `${count(first.episodes)} in ${pressesOf(first)}, before a wild encounter’s flash starts the loop again.`
}

/**
 * Finds the README's preview in `scheme` under the `docs/` of the checkout
 * `metaUrl` names.
 */
export const previewPath = (metaUrl: string, scheme: Scheme): string =>
  path.join(docsDir(metaUrl), 'assets', 'readme', `learning-${scheme}.gif`)

/**
 * Writes the README's preview in every scheme under the `docs/` of the checkout
 * `metaUrl` names, the walks `moments` hold played as `preview` sets out.
 */
export function writePreviews(
  metaUrl : string,
  moments : readonly Moment[] = walksOf(),
  preview : movie.Preview     = movie.PREVIEW
): void {
  for (const scheme of SCHEMES) {
    const target = previewPath(metaUrl, scheme)
    fs.mkdirSync(path.dirname(target), { recursive: true })
    fs.writeFileSync(target, encodeGif(movie.previewMovie(metaUrl, moments, preview, scheme)))
  }
}
