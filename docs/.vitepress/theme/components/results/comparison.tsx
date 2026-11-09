import { computed, defineComponent, ref } from 'vue'

import * as results      from '../../../lib/results/results.ts'
import { useDrawnWidth } from '../../../lib/widgets/width.ts'
import { ROLES }         from '../kit/hues.ts'
import * as plots        from '../kit/plots.tsx'

/**
 * The radius of a run's dot, in the pixels the strip's view box counts.
 */
const DOT = 4

/**
 * Draws one sample of a row in the hue of `role`: a dot for each run, and its
 * interquartile mean as a tick across the interval where it has one.
 */
function drawSample(sample: results.Sample, role: 'agent' | 'random') {
  const { fill, stroke } = ROLES[role]

  return (
    <g>
      {sample.interval === null ? null : (
        <path class={stroke} d={`M${sample.interval[0]},${sample.y}H${sample.interval[1]}`} {...plots.CURVE} />
      )}
      {sample.dots.map(x => <circle class={[fill, 'opacity-45']} cx={x} cy={sample.y} r={DOT} />)}
      <path class={stroke} d={`M${sample.mean},${sample.y - 2 * DOT}V${sample.y + 2 * DOT}`} {...plots.CURVE} />
    </g>
  )
}

/**
 * The comparison of each agent, trained with and without the curriculum,
 * against random presses under the same seeds, one row a group holding each
 * run's share of evaluation episodes reaching the starter at its last
 * evaluation beside its baseline's, and each sample's interquartile mean across
 * its interval. It draws nothing until a run is committed under `docs/runs/`.
 */
export const ResultsComparison = defineComponent({
  name  : 'ResultsComparison',
  setup : () => {
    const groups = results.groupsOf()
    const box    = ref<HTMLElement>()
    const width  = useDrawnWidth(box, 240)
    const strip  = computed(() => results.comparisonOf(groups, width.value))

    return () => groups.length === 0 ? null : (
      <div ref={box}>
        <svg aria-hidden="true" class="block h-auto w-full overflow-visible" viewBox={`0 0 ${strip.value.width} ${strip.value.height}`}>
          {plots.drawAxis(strip.value.grid)}
          {strip.value.labels.map(label => plots.drawLabel(label))}
          {strip.value.rows.map(row => [
            plots.drawLabel(row.name, plots.TITLE),
            drawSample(row.agent, 'agent'),
            drawSample(row.random, 'random')
          ])}
        </svg>
      </div>
    )
  }
})
