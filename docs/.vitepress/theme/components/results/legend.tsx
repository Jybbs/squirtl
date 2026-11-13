import { type PropType, defineComponent } from 'vue'

import type { LegendRow } from '../../../lib/results/legend.ts'
import { Key }            from '../kit/key.tsx'
import { LABEL }          from '../kit/widget.ts'

/**
 * The legend of the Results charts, each row naming what its marks decode
 * beside the key drawing them, set in one column on a narrow page and the head
 * beside its key on a wide one.
 */
export const ResultsLegend = defineComponent({
  name  : 'ResultsLegend',
  props : { rows: { required: true, type: Array as PropType<readonly LegendRow[]> } },
  setup : props => () => (
    <div class="results-legend grid gap-x-4 gap-y-1">
      {props.rows.map(row => [<span class={[LABEL, 'pt-1.5']}>{row.head}</span>, <Key entries={row.entries} />])}
    </div>
  )
})
