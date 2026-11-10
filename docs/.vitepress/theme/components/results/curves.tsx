import { defineComponent, ref, useId } from 'vue'

import { type Curve, type Curves, PLOTTING, useCurves } from '../../../lib/results/curves.ts'
import { SILHOUETTES, glyphOf }                         from '../../../lib/results/marks.ts'
import * as results                                     from '../../../lib/results/results.ts'
import { HUES, ROLES }                                  from '../kit/hues.ts'
import { Key }                                          from '../kit/key.tsx'
import * as plots                                       from '../kit/plots.tsx'
import { LABEL }                                        from '../kit/widget.ts'

/**
 * The words the widget sets: the label over the toggles, the heads over the
 * key's figures, and what the key's marks decode.
 */
const WORDS = {
  bedroom    : 'Solid, from the bedroom',
  curriculum : 'Hollow and dashed, with the curriculum',
  heads      : ['Reached it', 'Beats random'] as const,
  random     : 'Random presses',
  runs       : 'Runs, as many as you like'
}

/**
 * The key of the curves' marks, the glyph solid from the bedroom and hollow
 * along the curriculum, and random presses' level line.
 */
const KEY = [
  { mark: glyphOf({ agent: 'ppo', curriculum: false }), name: WORDS.bedroom, role: 'agent' as const },
  { mark: glyphOf({ agent: 'ppo', curriculum: true }), name: WORDS.curriculum, role: 'agent' as const },
  { name: WORDS.random, role: 'random' as const }
]

/**
 * The classes laying out the toggles, a grid of them as wide as each one's name
 * and figure need, each toggle its glyph, its name, and its last share, ringed
 * in its agent's hue while pressed.
 */
const PARTS = {
  group : 'results-toggles grid gap-2',
  item  : 'results-toggle focus-ring grid items-center gap-2 rounded-2 py-2 pr-3 pl-2 text-left',
  mark  : 'grid size-6 place-items-center *:size-4',
  name  : 'font-code text-label leading-snug font-semibold tracking-caps whitespace-nowrap uppercase',
  value : 'text-right font-code text-small leading-none font-medium tabular-nums'
}

/**
 * Draws `line`, one group's curve in its agent's hue, dashed for the
 * curriculum, with its agent's silhouette at each evaluation, shown up to the
 * share `shown` of the plot's width through the clip `clip`.
 */
function drawCurve(line: Curve, curves: Curves, shown: number, clip: string) {
  const { frame, across } = curves
  return [
    <clipPath id={clip}>
      <rect height={frame.floor + PLOTTING.gap} width={across * shown + PLOTTING.gap} x={frame.x(0, 1) - PLOTTING.gap} y={0} />
    </clipPath>,
    <g class={HUES[line.group.hue].ink} clip-path={`url(#${clip})`} display={shown > 0 ? undefined : 'none'}>
      <path class={['fill-none stroke-current', line.dashed ? 'results-dashed' : null]} d={line.d} {...plots.CURVE} />
      {line.points.map(([x, y]) => (
        <path class={line.dashed ? 'results-open' : 'results-solid'} d={SILHOUETTES[line.group.agent]} transform={`translate(${x} ${y})`} />
      ))}
    </g>
  ]
}

/**
 * Draws the toggle pressing `group`, its glyph, its name, and its last share.
 */
function drawToggle(group: results.Group, props: object, pressed: boolean) {
  return (
    <button {...props} class={[PARTS.item, pressed ? HUES[group.hue].text : 'text-quiet']} type="button">
      <span aria-hidden="true" class={PARTS.mark} innerHTML={glyphOf(group)} />
      <span class={PARTS.name}>{group.name}</span>
      <span class={PARTS.value}>{results.percent({ ...group.comparison.reached, interval: null })}</span>
    </button>
  )
}

/**
 * The learning curves of the groups a reader presses, any number at once on a
 * group of toggles each marked with its agent's glyph from the game, each
 * curve the interquartile mean of its runs' share of evaluation episodes
 * reaching the starter at each evaluation, beside random presses' share as a
 * level line. A pressed group's curve traces out along the steps and draws
 * back on release, and under the plot the figures of every group stand in a
 * fixed slot, lit while pressed. It draws nothing until a run is committed
 * under `docs/runs/`.
 */
export const ResultsCurves = defineComponent({
  name  : 'ResultsCurves',
  setup : () => {
    const box = ref<HTMLElement>()
    const id  = useId()
    const { curves, groups, random, toggles, traces, width } = useCurves(box)

    return () => groups.length === 0 || random === null ? null : (
      <div class="@container grid gap-4">
        <div class="grid gap-2">
          <span class={LABEL}>{WORDS.runs}</span>
          <div {...toggles.root.value} aria-label={WORDS.runs} class={PARTS.group}>
            {groups.map(group => drawToggle(group, toggles.item(group.id), toggles.pressed.value.has(group.id)))}
          </div>
        </div>
        <div class="relative h-results-plot" ref={box}>
          <svg {...plots.SVG} viewBox={`0 0 ${width.value} ${PLOTTING.height}`}>
            {plots.drawAxis(curves.value.grid)}
            {curves.value.labels.map(label => plots.drawLabel(label))}
            {curves.value.titles.map(title => plots.drawLabel(title, plots.TITLE))}
            <path
              class={['fill-none', ROLES.random.stroke]}
              d={`M${curves.value.frame.x(0, 1)},${curves.value.baseline}H${curves.value.frame.end}`}
              {...plots.CURVE}
            />
            {curves.value.lines.map((line, n) => drawCurve(line, curves.value, traces[n]!.value, `${id}-${n}`))}
          </svg>
        </div>
        <Key entries={KEY} />
        <Key entries={results.figuresOf(groups, random, toggles.pressed.value)} heads={WORDS.heads} />
      </div>
    )
  }
})
