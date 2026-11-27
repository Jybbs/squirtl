import { defineComponent } from 'vue'

import { EPISODES, MADE_UP } from '../../../lib/results/made-up.ts'
import { legendOf }          from '../../../lib/results/legend.ts'
import { hueOf }             from '../../../lib/results/results.ts'
import { HUES }              from '../kit/hues.ts'
import { LABEL, LIST }       from '../kit/widget.ts'
import { ResultsComparison } from '../results/comparison.tsx'

/**
 * The chart's own marks the cards draw large, read from its legend: a seed
 * risen from its random share, and each shade a cell takes.
 */
const KEY    = legendOf([{ agent: 'ppo' }], MADE_UP.random!, 'identity-results-hatch')
const SEED   = KEY.find(row => row.head === 'Last evaluation')!.entries[0]!.mark!
const SHADES = KEY.find(row => row.head === 'Share reaching the goal')!.entries.map(entry => entry.mark!)

/**
 * One run's row of cells, a cell an evaluation, in the shades its shares take.
 */
const RUN = '<svg viewBox="0 0 64 18">'
          + [0, 0, 1, 1, 2, 2, 3, 3].map((shade, n) =>
            `<rect class="results-cell-${shade}" x="${n * 8}" y="4" width="7" height="10"/>`).join('')
          + '</svg>'

/**
 * The cards, each a part of the chart, its mark as the chart draws it, and
 * what it stands for.
 */
const CARDS = [
  {
    mark : RUN,
    name : 'A run',
    says : 'One agent trained once under one seed, a cell for each of its evaluations.'
  },
  {
    mark : SEED,
    name : 'A seed',
    says : 'Sets one run’s luck. Its line runs from the tick marking random presses’ share under that seed '
         + 'to the run’s share at its last evaluation.'
  },
  {
    mark : SHADES.join(''),
    name : 'A share',
    says : `How many of an evaluation’s ${EPISODES} episodes reach the goal, a cell a shade stronger past `
         + 'none, a third, and two thirds.'
  }
]

/**
 * The comparison the Results pages draw, a lane an agent and a row a seed, on
 * made-up runs so it calls no measured result, beside three cards naming its
 * parts in its own marks.
 */
export const IdentityResults = defineComponent({
  name  : 'IdentityResults',
  setup : () => () => (
    <div class="@container">
      <div class="identity-results grid gap-6">
        <ul class={`${LIST} identity-results-cards grid gap-3`}>
          {CARDS.map(card => (
            <li class="identity-results-card m-0 grid content-start items-center gap-x-4 gap-y-1 p-4">
              <span
                aria-hidden="true"
                class={`${HUES[hueOf('ppo')].ink} identity-results-mark flex items-center gap-1`}
                innerHTML={card.mark}
              />
              <span class={LABEL}>{card.name}</span>
              <span class="text-note leading-snug text-ink">{card.says}</span>
            </li>
          ))}
        </ul>
        <ResultsComparison results={MADE_UP} />
      </div>
    </div>
  )
})
