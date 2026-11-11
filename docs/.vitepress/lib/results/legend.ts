import type { KeyEntry }                                     from '../widgets/chips.ts'
import { EDGES }                                             from './lanes.ts'
import { SILHOUETTES }                                       from './marks.ts'
import { AGENTS, type Estimate, type Group, hueOf, percent } from './results.ts'

/**
 * One row of the legend, what its marks decode beside them.
 */
export interface LegendRow {
  entries : readonly KeyEntry[]
  head    : string
}

/**
 * Names the share of a seed's episodes reaching the goal each shade a cell
 * takes marks, from none, up to each of `EDGES` past the first, then above
 * the last.
 */
const SHADES = [
  'None',
  ...EDGES.slice(1).map(edge => `Up to ${Math.round(edge * 100)}%`),
  `Above ${Math.round(EDGES.at(-1)! * 100)}%`
]

/**
 * Draws a mark of the legend as an SVG eighteen pixels on a side.
 */
const marked = (body: string) => `<svg viewBox="0 0 18 18">${body}</svg>`

/**
 * Draws a cell's swatch in `shade`, hatched through the pattern `hatch` where
 * it names one.
 */
function swatchOf(shade: number, hatch: string | null = null): string {
  const cell = '<rect x="2" y="4" width="14" height="10"'
  return marked(hatch === null
    ? `${cell} class="results-cell-${shade}"/>`
    : `<defs><pattern id="${hatch}" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">`
      + `<rect class="fill-ground" width="1.5" height="4"/></pattern></defs>`
      + `${cell} class="results-cell-${shade}"/>${cell} fill="url(#${hatch})"/>`)
}

/**
 * The track an odds mark sits on, from 0 to 100%.
 */
const TRACK = '<rect class="fill-rule" x="1" y="6" width="16" height="6" rx="1"/>'

/**
 * The entries decoding a lane's last evaluation, a seed risen from its random
 * share and the group's interquartile mean across its interval.
 */
const FINALS: readonly KeyEntry[] = [
  {
    mark : marked('<path class="stroke-quiet" d="M3,9H14" stroke-width="1.5"/>'
         + '<rect class="fill-random" x="1.5" y="3.5" width="3" height="11" rx="1"/>'
         + `<path class="results-solid" d="${SILHOUETTES.ppo}" transform="translate(14 9) scale(0.5)"/>`),
    name : 'A seed, from its random share',
    role : 'agent'
  },
  {
    mark : marked('<rect class="results-pale" x="1" y="3" width="16" height="12" rx="2"/><path class="results-mean" d="M9,3V15"/>'),
    name : 'Interquartile mean, 95% interval',
    role : 'agent'
  }
]

/**
 * The entries decoding a verdict, the odds of the higher return across their
 * interval and the tick at even odds.
 */
const VERDICT: readonly KeyEntry[] = [
  {
    mark : marked(`${TRACK}<path class="results-whisker" d="M3,9H15M3,5V13M15,5V13"/><circle class="fill-current" cx="10" cy="9" r="3"/>`),
    name : 'Odds of the higher return, 95% interval',
    role : 'agent'
  },
  { mark: marked(`${TRACK}<path class="results-even" d="M9,3V15"/>`), name: 'Even odds', role: 'none' }
]

/**
 * Lists the legend of the figure drawing `groups`, one row a thing its marks
 * decode, each entry the figure's own mark: each agent's hue, the hatching
 * along the curriculum, a cell's shade, the last evaluation, random presses'
 * share `random` across every seed, and the verdict's odds, the curriculum's
 * hatching drawn through the pattern `hatch`.
 */
export function legendOf(groups: readonly Group[], random: Estimate, hatch: string): LegendRow[] {
  const agents = [...new Set(groups.map(group => group.agent))]
  const band   = '<rect class="fill-random opacity-15" x="1" y="1" width="16" height="16"/>'
               + '<path class="stroke-random" d="M9,1V17" stroke-width="2"/>'

  return [
    { entries: agents.map(agent => ({ hue: hueOf(agent), mark: swatchOf(3), name: AGENTS[agent].short })), head: 'Agent' },
    {
      entries : [
        { mark: swatchOf(3), name: 'From the bedroom', role: 'agent' },
        { mark: swatchOf(3, hatch), name: 'With the curriculum', role: 'agent' }
      ],
      head : 'Start'
    },
    {
      entries : SHADES.map((name, shade) => ({ mark: swatchOf(shade), name, role: shade === 0 ? 'none' : 'agent' })),
      head    : 'Share reaching the goal'
    },
    { entries: FINALS, head: 'Last evaluation' },
    { entries: [{ mark: marked(band), name: 'Across every seed', role: 'random', value: percent(random) }], head: 'Random presses' },
    { entries: VERDICT, head: 'Verdict' }
  ]
}
