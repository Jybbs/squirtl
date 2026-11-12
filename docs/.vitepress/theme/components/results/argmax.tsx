import { defineComponent, ref } from 'vue'

import * as argmax                    from '../../../lib/results/argmax.ts'
import { useScrub }                   from '../../../lib/widgets/scrub.ts'
import { DETAIL, LABEL, SCRUB_PARTS } from '../kit/widget.ts'

/**
 * The classes of the widget's parts: the takeaway as its heading and the
 * sentence beneath it, the row of evaluations that serves as its slider and
 * each evaluation in it, the Brick Red mark naming a count, a lane's name,
 * its tiles, a seed's tile and the parts of its count, and the line naming
 * what the evaluation shows.
 */
const PARTS = {
  count   : 'grid justify-items-center gap-1 @sm:flex @sm:items-baseline',
  figure  : 'font-code text-body leading-none font-medium tabular-nums text-ink @sm:text-figure',
  head    : 'm-0 font-body text-say leading-snug font-semibold text-balance text-ink',
  lane    : 'grid gap-2',
  mark    : 'h-5 font-code text-label leading-snug font-semibold whitespace-nowrap tabular-nums',
  named   : 'rounded-1 bg-critical px-1 text-athens-gray',
  of      : 'font-code text-small leading-none text-quiet tabular-nums',
  pick    : 'results-pick grid justify-items-center gap-1 rounded-1 bg-lift py-1',
  picks   : 'focus-ring-within relative grid grid-cols-10 gap-1 rounded-1 select-none',
  says    : 'm-0 font-body text-small leading-normal text-quiet',
  status  : 'm-0 min-h-7 font-body text-body leading-normal text-ink @sm:min-h-5',
  thumb   : 'absolute top-0 left-0 outline-none',
  tile    : 'results-seed grid justify-items-center gap-1 rounded-1 bg-lift px-1 py-2',
  tiles   : 'grid grid-cols-5 gap-1'
}

/**
 * The words the widget sets: the label over the evaluations, the name a
 * screen reader reads for their slider, the word naming the most likely
 * press's count beside it, and a tile's seed.
 */
const WORDS = {
  likeliest : 'Likeliest',
  picks     : 'Seeds differing at each evaluation',
  seed      : (seed: number) => `Seed ${seed}`,
  slider    : 'The evaluation shown, each naming how many seeds differ'
}

/**
 * Draws the Brick Red mark naming `value`, after the word `word` where the
 * widget is wide enough to set it.
 */
function drawMark(value: number, word = '') {
  return (
    <span class={PARTS.named}>
      {word ? <span class="@max-sm:hidden">{`${word} `}</span> : null}
      {value}
    </span>
  )
}

/**
 * Draws the tile of `seeded` at evaluation `n`: its seed, its sampled count of
 * the episodes an evaluation plays, and the Brick Red mark of its count at the
 * most likely press where the two differ, in a slot holding its height either
 * way.
 */
function drawTile(seeded: argmax.Seeded, n: number, episodes: number) {
  const counts = seeded.counts[n]!
  return (
    <div class={PARTS.tile} data-differs={counts.differs ? '' : undefined}>
      <span class={DETAIL}>{WORDS.seed(seeded.seed)}</span>
      <span class={PARTS.count}>
        <span class={PARTS.figure}>{counts.sampled}</span>
        <span class={PARTS.of}>{`of ${episodes}`}</span>
      </span>
      <span class={PARTS.mark}>{counts.differs ? drawMark(counts.argmax, WORDS.likeliest) : null}</span>
    </div>
  )
}

/**
 * PPO's evaluations one at a time, under the takeaway every count gives as its
 * heading: each seed's tile in its start's lane holding the count of episodes
 * reaching the goal sampling its presses, marked in Brick Red with its count
 * at the most likely press only where the two differ, and above the lanes a
 * row of the evaluations naming how many seeds differ at each, which serves
 * as the slider choosing one through a press, a drag, or the arrow keys. It
 * opens on the last evaluation and draws nothing until a PPO run is committed
 * under `docs/runs/`.
 */
export const ResultsArgmax = defineComponent({
  name  : 'ResultsArgmax',
  setup : () => {
    const box  = ref<HTMLElement>()
    const laid = argmax.argmaxOf()
    if (laid === null) return () => null

    const at    = ref(laid.steps.length - 1)
    const scrub = useScrub(box, { beat: 0, done: () => true, finish: () => {}, tick: () => {} }, {
      at       : at,
      count    : laid.steps.length,
      describe : n => `${argmax.evaluationText(laid, n)}, ${argmax.differingText(laid, n)}`,
      label    : WORDS.slider,
      seek     : n => { at.value = n }
    })

    return () => (
      <div class="@container grid gap-4" ref={box}>
        <div class="grid gap-1">
          <p class={PARTS.head}>{laid.takeaway.head}</p>
          <p class={PARTS.says}>{laid.takeaway.says}</p>
        </div>
        <div {...scrub.root.value} class="grid gap-2">
          <span class={LABEL}>{WORDS.picks}</span>
          <div {...scrub.control.value} class={[SCRUB_PARTS.control, PARTS.picks]}>
            {laid.differing.map((differing, n) => (
              <span class={PARTS.pick} data-picked={n === at.value ? '' : undefined}>
                <span class={DETAIL}>{n + 1}</span>
                <span class={PARTS.mark}>{differing > 0 ? drawMark(differing) : null}</span>
              </span>
            ))}
            <span {...scrub.thumb.value} class={PARTS.thumb} />
          </div>
        </div>
        <div class="grid gap-1">
          <span class={LABEL}>{argmax.evaluationText(laid, at.value)}</span>
          <p class={PARTS.status}>{argmax.differingText(laid, at.value)}</p>
        </div>
        {laid.lanes.map(lane => (
          <section class={PARTS.lane}>
            <span class={LABEL}>{lane.group.name}</span>
            <div class={PARTS.tiles}>{lane.seeds.map(each => drawTile(each, at.value, laid.episodes))}</div>
          </section>
        ))}
      </div>
    )
  }
})
