import { defineComponent, ref, useId } from 'vue'

import { useComparison }                                                        from '../../../lib/results/fold.ts'
import { LANES, type Lane, type Lanes, type OddsLine, type SeedRow, type Side } from '../../../lib/results/lanes.ts'
import { SILHOUETTES }                                                          from '../../../lib/results/marks.ts'
import { HUES, ROLES }                                                          from '../kit/hues.ts'
import * as plots                                                               from '../kit/plots.tsx'
import { ResultsLegend }                                                        from './legend.tsx'

/**
 * What a screen reader reads for each side a reader widens.
 */
const SIDES: Readonly<Record<Side, string>> = {
  curves : 'Learning curves, widened while focused',
  finals : 'Last evaluation, widened while focused'
}

/**
 * The classes of what a verdict compares against, in the code face's quiet
 * capitals, and of a lane's name and a verdict's word, in its agent's text
 * step.
 */
const CAPS = {
  against : `${plots.TICK} tracking-caps`,
  named   : 'fill-current font-code text-label font-semibold tracking-caps'
}

/**
 * Draws one seed's row of cells in its agent's hue, hatched along the
 * curriculum, traced out to the share `shown` of its width through its clip.
 */
function drawRow(row: SeedRow, shown: number, clip: string, hatch: string) {
  return [
    <clipPath id={clip}><rect height={LANES.row + 2} width={row.clip.width * shown} x={row.clip.x} y={row.clip.y} /></clipPath>,
    <g clip-path={`url(#${clip})`}>
      {row.cells.map(cell => <rect class={`results-cell-${cell.shade}`} height={LANES.row} width={cell.width} x={cell.x} y={row.y} />)}
      {row.hatch ? <rect fill={`url(#${hatch})`} height={LANES.row} width={row.hatch.width} x={row.hatch.x} y={row.y} /> : null}
    </g>
  ]
}

/**
 * Draws one verdict, its label, its odds as a whisker on a track from 0 to
 * 100% with a tick at even odds, and its word in the agent's text step.
 */
function drawOdds({ label, odds, word }: OddsLine) {
  const { at, even, interval, wide, x, y } = odds
  return [
    plots.drawLabel(label, CAPS.against),
    <rect class="fill-rule" height={6} rx={1} width={wide} x={x} y={y - 3} />,
    <path class="results-even" d={`M${even},${y - 6}V${y + 6}`} />,
    interval ? <path class="results-whisker" d={`M${interval[0]},${y}H${interval[1]}M${interval[0]},${y - 4}V${y + 4}M${interval[1]},${y - 4}V${y + 4}`} /> : null,
    <circle class="fill-current" cx={at} cy={y} r={3.5} />,
    plots.drawLabel(word, CAPS.named)
  ]
}

/**
 * Draws a lane's last evaluation: random presses' interval and interquartile
 * mean, the group's interval and interquartile mean, and each seed risen to
 * the share `risen` of the way from its random share to its own.
 */
function drawFinals(lane: Lane, risen: number) {
  const { interval, mean, random, span } = lane.finals
  const tall = span[1] - 8
  return [
    <rect class={[ROLES.random.fill, 'opacity-15']} height={span[1]} width={random.interval[1] - random.interval[0]} x={random.interval[0]} y={span[0]} />,
    <path class={ROLES.random.stroke} d={`M${random.mean},${span[0]}v${span[1]}`} stroke-width={2} />,
    <rect class="results-pale" height={tall + 4} rx={3} width={Math.max(2, interval[1] - interval[0]) + 4} x={Math.min(interval[0], interval[1] - 2) - 2} y={span[0] + 2} />,
    <path class="results-mean" d={`M${mean},${span[0] + 2}v${tall + 4}`} />,
    ...lane.bells.map(bell => {
      const to = bell.from + (bell.to - bell.from) * risen
      return (
        <g>
          <path class="stroke-quiet" d={`M${bell.from},${bell.y}H${to}`} stroke-width={1.5} />
          <rect class={ROLES.random.fill} height={11} rx={1} width={3} x={bell.from - 1.5} y={bell.y - 5.5} />
          <path class="results-solid" d={SILHOUETTES[lane.group.agent]} opacity={risen > 0 ? 1 : 0} transform={`translate(${to} ${bell.y}) scale(0.5)`} />
        </g>
      )
    })
  ]
}

/**
 * Draws one group's lane in its agent's hue: its glyph and heads, its rows,
 * its last evaluation, its verdicts as far as they have opened, and its tab
 * as far as the last evaluation has folded.
 */
function drawLane(lane: Lane, n: number, drawn: Lanes, motion: Motion) {
  const { group } = lane
  return (
    <g class={HUES[group.hue].ink}>
      {lane.glyphs.map(([x, y]) => (
        <path class={group.curriculum ? 'results-open' : 'results-solid'} d={SILHOUETTES[group.agent]} transform={`translate(${x} ${y}) scale(0.85)`} />
      ))}
      <g class={HUES[group.hue].text}>{plots.drawLabel(lane.heads[0]!, CAPS.named)}</g>
      {plots.drawLabel(lane.heads[1]!)}
      <g opacity={1 - drawn.folded.curves}>{lane.rows.map((row, k) => drawRow(row, motion.rows[k]!, `${motion.id}-${n}-${k}`, `${motion.id}-hatch`))}</g>
      <g opacity={1 - drawn.folded.finals}>{drawFinals(lane, motion.bells[n]!)}</g>
      {drawn.opened > 0 ? <g class={HUES[group.hue].text} opacity={drawn.opened}>{lane.odds.flatMap(line => drawOdds(line))}</g> : null}
      {drawn.folded.finals > 0 ? <g class={HUES[group.hue].text} opacity={drawn.folded.finals}>{drawOdds(lane.tab)}</g> : null}
    </g>
  )
}

/**
 * Where the figure stands in its entrance, the share each seed's row has
 * traced out and each lane's seeds have risen, beside the ids its clips take.
 */
interface Motion {
  bells : readonly number[]
  id    : string
  rows  : readonly number[]
}

/**
 * Draws the figure: the axes along the steps and the shares, each fading as
 * its side folds, then every lane.
 */
function drawFigure(drawn: Lanes, motion: Motion) {
  return [
    <defs>
      <pattern height={4} id={`${motion.id}-hatch`} patternTransform="rotate(45)" patternUnits="userSpaceOnUse" width={4}>
        <rect class="fill-ground" height={4} width={1.5} />
      </pattern>
    </defs>,
    <g opacity={1 - drawn.folded.curves}>
      {plots.drawAxis(drawn.steps.grid)}
      {drawn.steps.labels.map(label => plots.drawLabel(label))}
      {drawn.steps.titles.map(title => plots.drawLabel(title, plots.TITLE))}
    </g>,
    <g opacity={1 - drawn.folded.finals}>
      {plots.drawAxis(drawn.shares.grid)}
      {drawn.shares.labels.map(label => plots.drawLabel(label))}
      {drawn.shares.titles.map(title => plots.drawLabel(title, plots.TITLE))}
    </g>,
    ...drawn.lanes.map((lane, n) => drawLane(lane, n, drawn, motion))
  ]
}

/**
 * The comparison of every group in one figure, a lane a group: each seed a row
 * of cells along the steps shaded in its agent's hue by its share of
 * evaluation episodes reaching the goal, hatched along the curriculum, and
 * at the right each seed's last evaluation risen from its random share beside
 * the group's interval, with its verdicts against random presses and, along
 * the curriculum, against the bedroom. Pointing at or focusing either side
 * widens it and folds the other to its tab, and under the figure a legend
 * decodes each mark under what it marks. It draws nothing until a run is
 * committed under `docs/runs/`.
 */
export const ResultsComparison = defineComponent({
  name  : 'ResultsComparison',
  setup : () => {
    const box = ref<HTMLElement>()
    const id  = useId()
    const { drawn, entrance, groups, legend, listeners, width } = useComparison(box, `${id}-key`)

    return () => groups.length === 0 ? null : (
      <div class="@container grid gap-4">
        <div class="relative" ref={box}>
          <svg aria-hidden="true" class="block h-auto w-full overflow-visible" viewBox={`0 0 ${width.value} ${drawn.value.height}`}>
            {drawFigure(drawn.value, { bells: entrance.bells.map(each => each.value), id, rows: entrance.rows.map(each => each.value) })}
          </svg>
          {(['curves', 'finals'] as const).map(side => drawn.value.sides === null ? null : (
            <div
              aria-label={SIDES[side]}
              class="results-side focus-ring absolute inset-y-0 rounded-1"
              role="group"
              style={{ left: `${drawn.value.sides[side][0]}px`, width: `${drawn.value.sides[side][1] - drawn.value.sides[side][0]}px` }}
              tabindex={0}
              {...listeners(side)}
            />
          ))}
        </div>
        <ResultsLegend rows={legend} />
      </div>
    )
  }
})
