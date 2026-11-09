import { computed, defineComponent, ref } from 'vue'

import * as results      from '../../../lib/results/results.ts'
import { useDrawnWidth } from '../../../lib/widgets/width.ts'
import { ROLES }         from '../kit/hues.ts'
import { Key }           from '../kit/key.tsx'
import * as plots        from '../kit/plots.tsx'

/**
 * The words the widget sets, the label over the groups a reader picks among
 * and the heads over the key's figures.
 */
const WORDS = {
  groups : 'Runs',
  heads  : ['Reached it', 'Beats random'] as const
}

/**
 * The learning curves of the runs of one agent and one curriculum, each run's
 * share of evaluation episodes reaching the starter at each evaluation it
 * played beside the random baseline's interquartile mean as a level line, the
 * group a press on the key above it picks. It draws nothing until a run is
 * committed under `docs/runs/`.
 */
export const ResultsCurves = defineComponent({
  name  : 'ResultsCurves',
  setup : () => {
    const groups = results.groupsOf()
    const box    = ref<HTMLElement>()
    const picked = ref(0)
    const width  = useDrawnWidth(box, 240)
    const curves = computed(() => results.curvesOf(groups[picked.value]!, results.PLOTTING.height, width.value))

    return () => groups.length === 0 ? null : (
      <div class="@container grid gap-3">
        <Key
          entries={groups.map(group => ({ name: group.name, role: 'agent' as const }))}
          label={WORDS.groups}
          onPress={(n: number) => { picked.value = n }}
          pressable
          pressed={picked.value}
        />
        <Key entries={results.keyOf(groups[picked.value]!)} heads={WORDS.heads} />
        <div class="relative h-results-plot" ref={box}>
          <svg {...plots.SVG} viewBox={`0 0 ${width.value} ${results.PLOTTING.height}`}>
            {plots.drawAxis(curves.value.grid)}
            {curves.value.labels.map(label => plots.drawLabel(label))}
            <path
              class={['fill-none', ROLES.random.stroke]}
              d={`M${curves.value.frame.x(0, 1)},${curves.value.baseline}H${curves.value.frame.end}`}
              {...plots.CURVE}
            />
            {curves.value.lines.map(line => <path class={['fill-none', ROLES.agent.stroke]} d={line} {...plots.CURVE} />)}
          </svg>
        </div>
      </div>
    )
  }
})
