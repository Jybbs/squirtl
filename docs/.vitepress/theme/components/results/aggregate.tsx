import { type Ref, type VNode, defineComponent, ref } from 'vue'

import * as aggregateColumns                    from '../../../lib/results/aggregate-columns.ts'
import { type Seeds, committedSeeds, useSeeds } from '../../../lib/results/aggregate-switches.ts'
import * as aggregate                           from '../../../lib/results/aggregate.ts'
import { useMotion }                            from '../../../lib/widgets/motion.ts'
import { useDrawnWidth }                        from '../../../lib/widgets/width.ts'
import { LABEL, LIST }                          from '../kit/widget.ts'
import { type Plot, WIDTH, drawPlot }           from './aggregate-columns.tsx'

/**
 * The classes of the widget's parts: one column laid over the plot and the
 * list of them, the drawing inside the plot, the plot and the switches
 * beside it, the line saying where the intervals come from, a switch's seed,
 * one switch and the list of them, and the side holding them.
 */
const PARTS = {
  column   : 'focus-ring block size-full cursor-pointer rounded-1 border-0 bg-transparent p-0 '
           + 'transition-colors data-[state=on]:bg-lift',
  columns  : [LIST, 'absolute inset-y-0 right-0 grid auto-cols-fr grid-flow-col'],
  drawing  : 'pointer-events-none absolute inset-0',
  layout   : 'grid gap-x-6 gap-y-3 @sm:grid-cols-4',
  plot     : 'relative h-race-plot @sm:col-span-3',
  says     : 'm-0 font-body text-small leading-normal text-quiet @sm:col-span-4',
  seed     : 'font-code text-label leading-snug font-semibold tracking-caps whitespace-nowrap uppercase',
  side     : 'grid content-start gap-2',
  switch   : 'focus-ring grid w-full justify-items-center rounded-1 border-hairline border-rule bg-lift '
           + 'px-2 py-1 text-quiet transition-colors motion-reduce:transition-none '
           + 'data-[state=on]:border-ink data-[state=on]:text-ink',
  switches : [LIST, 'grid grid-cols-3 gap-2 sm:grid-cols-5 @sm:grid-cols-1 @sm:content-start']
}

/**
 * Draws the plot over `aggregates` inside the element `plot` holds, a button
 * over each column that `opening` opens its runs from, the drawing `width`
 * wide beneath them, and the runs of the column a reader picked as a screen
 * reader reads them.
 */
function drawColumns(
  aggregates : readonly aggregate.Aggregate[],
  drawn      : Plot,
  opening    : ReturnType<typeof aggregateColumns.useOpen>,
  plot       : Ref<HTMLElement | undefined>,
  width      : number
): VNode {
  const picked = opening.picked.value
  const spoken = aggregates.map(each => aggregate.spokenOf(each)).join('. ')
  return (
    <div class={PARTS.plot} onPointerleave={opening.leave} onPointermove={opening.point} ref={plot}>
      <ul
        {...opening.columns.root.value}
        aria-label="Runs by group"
        class={PARTS.columns}
        style={{ left: `${WIDTH.scale}px` }}
      >
        {aggregates.map((each, n) => (
          <li>
            <button
              {...opening.columns.item(`${n}`)}
              aria-label={`${aggregate.whoOf(each)}, its runs`}
              class={PARTS.column}
              type="button"
            />
          </li>
        ))}
      </ul>
      <div aria-label={spoken} class={PARTS.drawing} role="img">
        {drawPlot(drawn, width)}
      </div>
      <p aria-live="polite" class="sr-only">
        {picked === null ? '' : aggregateColumns.spokenRunsOf(aggregates[picked]!, drawn.seeds)}
      </p>
    </div>
  )
}

/**
 * Draws the switch of each seed `kept` holds beneath the count of runs each
 * group keeps.
 */
function drawSeeds({ flipped, press, seeds, switches }: Seeds): VNode {
  const count = seeds.value.length
  return (
    <div class={PARTS.side}>
      <span class={LABEL}>{`Seeds kept, ${count} ${count === 1 ? 'run' : 'runs'} each`}</span>
      <ul {...switches.root.value} aria-label="Seeds kept" class={PARTS.switches}>
        {committedSeeds.map((seed, k) => (
          <li>
            <button
              {...switches.item(`${seed}`)}
              {...press}
              class={PARTS.switch}
              ref={(el: unknown) => { flipped[k] = el as Element | null }}
              type="button"
            >
              <span class={PARTS.seed}>{`Seed ${seed}`}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

/**
 * The aggregate every comparison reports, as columns over one scale of the
 * share reaching the starter, each group's interquartile mean a Poké Ball
 * standing at its height inside its 95% interval, and random presses under
 * the same seeds a band across every column. Switching a seed off leaves its
 * run out of every group and of random presses alike, so the means, the
 * counts of runs, and the intervals, then drawn here from 9,999 draws of the
 * seeds kept, glide together to their new places as their figures count
 * along. A ball whose mean moved rocks as it lands, random presses' band
 * settles as it lands, and the switched seed's run pops as it empties or
 * fills while its switch hops as the seed is kept or shakes as it is left
 * out, each switch sinking as it is pressed and springing back as it is let
 * go. A column a mouse rests on, or one a reader presses or picks from the
 * keyboard, opens out its runs in place of its ball, a press on one of them
 * switching its seed. Nothing is drawn until a run is committed.
 */
export const ResultsAggregate = defineComponent({
  name  : 'ResultsAggregate',
  setup : () => {
    const aggregates = aggregate.aggregatesOf()
    if (aggregates.length === 0) return () => null

    const plot    = ref<HTMLElement>()
    const width   = useDrawnWidth(plot, 240)
    const motion  = useMotion()
    const kept    = useSeeds(aggregateColumns.MOVE.rock)
    const opening = aggregateColumns.useOpen(plot, aggregates.length, WIDTH.scale)
    const shown   = aggregateColumns.useColumns(aggregates, kept.seeds)
    const means   = () => shown.columns.value.map(({ estimate }) => estimate.value)
    const balls   = aggregateColumns.useLanding(means)
    const band    = aggregateColumns.useLanding(() => [shown.random.value.value], aggregateColumns.SETTLE)
    const popped  = aggregateColumns.useSwitched(() => kept.seeds.value)

    return () => {
      const drawn: Plot = {
        balls   : balls,
        band    : band,
        columns : shown.columns.value,
        open    : opening.open.value,
        popped  : popped,
        random  : shown.random.value,
        seeds   : kept.seeds.value,
        still   : !motion.value,
        toggle  : kept.toggle
      }
      return (
        <div class="@container">
          <div class={PARTS.layout}>
            {drawColumns(aggregates, drawn, opening, plot, width.value)}
            {drawSeeds(kept)}
            <p aria-live="polite" class={PARTS.says}>{shown.note.value}</p>
          </div>
        </div>
      )
    }
  }
})
