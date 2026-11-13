import { useTransition } from '@vueuse/core'
import { type PropType, computed, defineComponent, nextTick, ref, watch } from 'vue'

import type * as rooms            from '../../../../lib/game/rooms.ts'
import { IDENTITY }               from '../../../../lib/identity/identity.ts'
import { FLAG_BITS, TRACE, byte } from '../../../../lib/methods/memory.ts'
import * as marks                 from '../../../../lib/methods/memory/marks.ts'
import type { Frame }             from '../../../../lib/methods/memory/play.ts'
import { useMotion }              from '../../../../lib/widgets/motion.ts'

/**
 * The parts of the overlay the key's entries set back, each entry's list in
 * the key's order, and the part each entry sets in a heavier stroke.
 */
type Part = 'bytes' | 'goal' | 'grid' | 'milestone'

const DIMS: readonly (readonly Part[])[] = [
  ['milestone', 'goal', 'bytes'],
  ['milestone', 'goal', 'bytes', 'grid'],
  ['goal', 'bytes', 'grid'],
  ['milestone', 'bytes', 'grid'],
  ['milestone', 'goal', 'grid']
]

const BOLD: readonly (Part | null)[] = [null, null, 'milestone', 'goal', 'bytes']

/**
 * The stroke and the fill of a flag's site in each term's hue.
 */
const SITE_HUES = {
  goal      : { fill: 'fill-amethyst-mark', stroke: 'stroke-amethyst-mark' },
  milestone : { fill: 'fill-heath-mark', stroke: 'stroke-heath-mark' },
  novelty   : { fill: 'fill-fern-mark', stroke: 'stroke-fern-mark' }
} as const

/**
 * Reads the rectangle a flag's site takes on the map fitted at `fit`, its
 * square inset a unit or its whole row.
 */
function siteBox(site: marks.Site, fit: marks.Fit): { height: number, width: number, x: number, y: number } {
  if (site.row !== undefined) return { height: fit.cell, width: fit.width, x: fit.left, y: fit.top + site.row * fit.cell }
  return { height: fit.cell - 2, width: fit.cell - 2, x: fit.left + site.at![0] * fit.cell + 1, y: fit.top + site.at![1] * fit.cell + 1 }
}

/**
 * Reads the classes that set `part` back while the key's entry `lit` picks out
 * another.
 */
const dimOf = (lit: number | null, part: Part) => [
  'motion-safe:transition-opacity',
  lit !== null && DIMS[lit]!.includes(part) ? 'opacity-30' : null
]

/**
 * Reads the stroke `part` takes, heavier while the key's entry `lit` picks it
 * out.
 */
const widthOf = (lit: number | null, part: Part, base: number) => lit !== null && BOLD[lit] === part ? 3.5 : base

/**
 * Draws the site of each flag the reward reads in the room `frame` shows,
 * dashed until its flag is set, then filled and sending one ring out.
 */
function drawSites(frame: Frame, fit: marks.Fit, lit: number | null) {
  const { flags } = TRACE[frame.row]!
  return marks.SITES.filter(site => site.place === frame.place).map(site => {
    const { term } = FLAG_BITS.find(each => each.flag === site.flag)!
    const hues     = SITE_HUES[term]
    const on       = flags.has(site.flag)
    const box      = siteBox(site, fit)
    return (
      <g class={dimOf(lit, term as Part)} key={site.flag}>
        <rect {...box} class={[hues.fill, on ? null : 'opacity-0', 'motion-safe:transition-opacity']} fill-opacity="0.3" />
        {on ? <rect {...box} class={['memory-pulse fill-none', hues.stroke]} stroke-width="2" /> : null}
        <rect {...box} class={['fill-none', hues.stroke]} stroke-dasharray={on ? undefined : '4 3'} stroke-width={widthOf(lit, term as Part, 2)} />
      </g>
    )
  })
}

/**
 * Draws a tick over every column and beside every row of the map fitted at
 * `fit`.
 */
function drawTicks(fit: marks.Fit, lit: number | null) {
  const { cell, cols, left, rows, top } = fit
  return (
    <g class={['stroke-quiet', dimOf(lit, 'grid')]} stroke-width="1">
      {Array.from({ length: cols }, (_, c) => <line x1={left + (c + 0.5) * cell} x2={left + (c + 0.5) * cell} y1={top - 5} y2={top - 1} />)}
      {Array.from({ length: rows }, (_, r) => <line x1={left - 5} x2={left - 1} y1={top + (r + 0.5) * cell} y2={top + (r + 0.5) * cell} />)}
    </g>
  )
}

/**
 * Draws the bytes' square at `at` on the map fitted at `fit`, its two rules
 * running to the map's edges, where the numbers of `target` stand.
 */
function drawBytes(fit: marks.Fit, target: rooms.Square, at: readonly [number, number], lit: number | null) {
  const { cell, left, top } = fit
  const [x, y]              = at
  const cx                  = left + (x + 0.5) * cell
  const cy                  = top + (y + 0.5) * cell
  return (
    <g class={dimOf(lit, 'bytes')}>
      <line class="stroke-denim-mark" stroke-dasharray="3 3" stroke-width="1.5" x1={cx} x2={cx} y1={top - 6} y2={cy} />
      <line class="stroke-denim-mark" stroke-dasharray="3 3" stroke-width="1.5" x1={left - 6} x2={cx} y1={cy} y2={cy} />
      <rect class="fill-none stroke-denim-mark" height={cell} stroke-width={widthOf(lit, 'bytes', 2)} width={cell} x={left + x * cell} y={top + y * cell} />
      <text class="fill-denim-mark font-code font-semibold tabular-nums" font-size="13" text-anchor="middle" x={cx} y={top - 9}>{byte(target[0])}</text>
      <text class="fill-denim-mark font-code font-semibold tabular-nums" font-size="13" text-anchor="end" x={left - 9} y={cy + 4}>{byte(target[1])}</text>
    </g>
  )
}

/**
 * The overlay over the map: a dashed site where the game sets each flag the
 * reward reads, filled once it is set and sending one ring out as it is, a
 * tick for every column and row, and the bytes' square with its two rules and
 * its numbers at the map's edges, gliding to each square the bytes name on one
 * room and jumping to a new one. Picking out an entry of the key sets back
 * every part it does not name.
 */
export const MemoryOverlay = defineComponent({
  name: 'MemoryOverlay',

  props: {
    fit    : { required: true, type: Object as PropType<marks.Fit> },
    frame  : { required: true, type: Object as PropType<Frame> },
    lit    : { default: null, type: Number as PropType<number | null> },
    target : { required: true, type: Array as unknown as PropType<rooms.Square> }
  },

  setup: props => {
    const motion = useMotion()
    const jump   = ref(false)
    const ring   = useTransition(() => [props.target[0], props.target[1]], {
      disabled : computed(() => !motion.value || jump.value),
      duration : marks.TIMING.glide,
      easing   : [...IDENTITY.motion.curve] as [number, number, number, number]
    })

    watch(() => props.frame.place, () => {
      jump.value = true
      void nextTick(() => { jump.value = false })
    }, { flush: 'sync' })

    return () => (
      <svg
        aria-hidden="true"
        class="pointer-events-none absolute inset-0 block size-full overflow-visible"
        style={{ opacity: 1 - props.frame.fade / 3 }}
        viewBox={`0 0 ${marks.PLATE.width} ${marks.PLATE.height}`}
      >
        {drawSites(props.frame, props.fit, props.lit)}
        {drawTicks(props.fit, props.lit)}
        {drawBytes(props.fit, props.target, ring.value as [number, number], props.lit)}
      </svg>
    )
  }
})
