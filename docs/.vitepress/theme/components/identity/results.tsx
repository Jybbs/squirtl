import { defineComponent, useId } from 'vue'

import { SAMPLE, lookOf } from '../../../lib/results/legend.ts'
import { ResultsLegend }  from '../results/legend.tsx'

/**
 * The look the Results charts share, every part they draw named by its row of
 * the legend, drawn on made-up groups and a made-up share for random presses
 * so it calls no measured result.
 */
export const IdentityResults = defineComponent({
  name  : 'IdentityResults',
  setup : () => {
    const id = useId()
    return () => (
      <div class="@container">
        <ResultsLegend rows={lookOf(SAMPLE.groups, SAMPLE.random, `${id}-key`)} />
      </div>
    )
  }
})
