import { computed, defineComponent, ref } from 'vue'

import { marks }         from '../../../lib/front/reward.ts'
import * as discount     from '../../../lib/methods/discount.ts'
import { count, fixed }  from '../../../lib/widgets/numbers.ts'
import { useScrub }      from '../../../lib/widgets/scrub.ts'
import { useDrawnWidth } from '../../../lib/widgets/width.ts'
import { Chip }          from '../kit/chip.tsx'
import { ROLES }         from '../kit/hues.ts'
import * as plots        from '../kit/plots.tsx'
import { COVER, LABEL }  from '../kit/widget.ts'

/**
 * The words the widget sets, the label over the starter's chips, the axes'
 * titles, and the name a screen reader reads for the slider.
 */
const WORDS = {
  ahead   : 'Steps until the payment arrives, on a log scale',
  slider  : 'The discount, set by dragging the point where a payment counts half',
  starter : 'The starter counts',
  weight  : 'Weight'
}

/**
 * The fill each term's dot takes, a milestone in Heath and the starter in
 * Amethyst.
 */
const TERM_FILL = { milestone: 'fill-heath-mark', starter: 'fill-amethyst-mark' } as const

/**
 * Describes the half point at `stop` for a screen reader.
 */
function describe(stop: number): string {
  const at = discount.discountAt(stop)
  return `Discount ${discount.spelled(at)}, half its weight at ${count(Math.round(discount.halfLife(at)))} steps`
}

/**
 * Draws the lane of `plot`: each episode's tiles along the top, edged in its
 * player's hue and holding the game's mark for its payment, a hairline from
 * each group down to its payments on the curve, and each payment's dot filled
 * in its term's hue and ringed in its player's.
 */
function drawLane(plot: discount.WeightPlot) {
  const { lane, tile } = discount.WEIGHING

  return [
    ...plot.lanes.flatMap(({ groups, player }) => groups.map(group => (
      <g class={ROLES[player].stroke}>
        <path class="fill-none" d={group.leader} stroke-width={discount.STROKES.axis} />
        {group.tiles.map(({ arrival, x }) => [
          <rect class="fill-athens-gray" height={tile} rx="3" stroke-width={discount.STROKES.line} width={tile} x={x - tile / 2} y={lane} />,
          <svg height="16" innerHTML={marks[arrival.term]} width="16" x={x - 8} y={lane + 3} />
        ])}
      </g>
    ))),
    ...plot.dots.map(dot => (
      <circle class={[TERM_FILL[dot.term], ROLES[dot.player].stroke]} cx={dot.x} cy={dot.y} r="4.5" stroke-width={discount.STROKES.line} />
    ))
  ]
}

/**
 * Draws the chips over the chart: what each episode's starter counts under
 * `at`, and the discount itself, named the setting where it is the one the
 * settings declare.
 */
function drawFigures(at: number) {
  return (
    <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
      <span class={LABEL}>{WORDS.starter}</span>
      {discount.EPISODES.map(episode => (
        <Chip
          name={episode.name}
          role={episode.player}
          value={fixed(discount.weightOf(at, episode.starter), 4)}
        />
      ))}
      <Chip class="ml-auto" name={at === discount.DISCOUNT ? 'The setting' : 'Discount'} value={discount.spelled(at)} />
    </div>
  )
}

/**
 * The weight a payment carries against the steps until it arrives on a log
 * scale, the agent's walk's and a random wander's milestones and starter on the
 * curve and their marks in one lane along the top, and the point where a
 * payment counts half as the handle that sets the discount, which a press or a
 * drag along the chart or the arrow keys move, each named discount catching it
 * as it passes. The chips above it read what each episode's starter counts.
 */
export const MethodsDiscount = defineComponent({
  name  : 'MethodsDiscount',
  setup : () => {
    const box   = ref<HTMLElement>()
    const at    = ref(discount.stopOf(discount.DISCOUNT))
    const width = useDrawnWidth(box, discount.LEAST)
    const set   = computed(() => discount.discountAt(at.value))
    const plot  = computed(() => discount.plotOf(set.value, width.value))
    const scrub = useScrub(box, { beat: 0, done: () => true, finish: () => {}, tick: () => {} }, {
      at       : at,
      count    : discount.WEIGHING.stops + 1,
      describe : describe,
      label    : WORDS.slider,
      seek     : stop => { at.value = stop }
    })

    return () => {
      const { box: room, height } = discount.WEIGHING
      const { floor, half }       = plot.value

      return (
        <div class="@container grid gap-3">
          {drawFigures(set.value)}
          <div {...scrub.root.value} class="relative" ref={box}>
            <svg aria-hidden="true" class="block h-auto w-full overflow-visible" viewBox={`0 0 ${width.value} ${height}`}>
              {plots.drawAxis(plot.value.grid)}
              {plot.value.labels.map(label => plots.drawLabel(label))}
              {plots.drawLabel({ anchor: 'end', text: WORDS.ahead, x: width.value - room.right, y: floor + 42 }, plots.TITLE)}
              {plots.drawLabel({ anchor: 'start', text: WORDS.weight, x: room.left - 36, y: room.top - 16 }, plots.TITLE)}
              {plot.value.stops.map(x => <path class="stroke-quiet" d={`M${x},${half.y - 5}V${half.y + 5}`} stroke-width={discount.STROKES.axis} />)}
              <path class={['fill-none', ROLES.agent.stroke]} d={plot.value.curve} {...plots.CURVE} />
              {drawLane(plot.value)}
              <path class="stroke-quiet" d={`M${half.x},${half.y}V${floor}`} stroke-dasharray="3 3" stroke-width={discount.STROKES.reference} />
              <circle class="fill-ground stroke-rule" cx={half.x} cy={half.y} r="11" />
              <circle class={ROLES.agent.fill} cx={half.x} cy={half.y} r="6" />
              {plots.drawLabel(half.label, plots.TITLE)}
            </svg>
            <div {...scrub.control.value} class={COVER.control} />
            <div {...scrub.thumb.value} class={COVER.thumb} />
          </div>
        </div>
      )
    }
  }
})
