import * as watching     from '../../../../lib/commands/watch.ts'
import { padMark }       from '../../../../lib/game/pad.ts'
import { Chip }          from '../../kit/chip.tsx'
import { DETAIL, LABEL } from '../../kit/widget.ts'

/**
 * The marks a check's chip shows while it waits, while it compares, and once
 * it matches, beside the word its value reads.
 */
const CHECKS = {
  pass : {
    mark  : '<svg viewBox="0 0 16 16"><path d="M3.5 8.5l3 3 6-7" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    value : 'matches'
  },
  run : {
    mark  : '<svg viewBox="0 0 16 16"><path d="M3 8h2M7 8h2M11 8h2" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/></svg>',
    value : 'comparing'
  },
  wait : {
    mark  : '<svg viewBox="0 0 16 16"><path d="M8 3a5 5 0 1 1 0 10a5 5 0 1 1 0-10z" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>',
    value : 'waiting'
  }
} as const

/**
 * The words the checks set.
 */
const WORDS = {
  after  : 'Once the last press plays',
  before : 'Before a press plays',
  intro  : 'After the intro',
  record : 'In run.json'
}

/**
 * Draws a check's chip named `name` where it stands at `check`.
 */
const drawCheck = (name: string, check: watching.Check) => (
  <Chip class={['watch-status w-full', `watch-${check}`]} mark={CHECKS[check].mark} name={name} value={CHECKS[check].value} />
)

/**
 * Draws one side of the digest's comparison under `label`, its digits faint
 * until the intro writes them and set in ink once they match.
 */
function drawDigest(label: string, digits: { matched: boolean, revealed: number }) {
  return (
    <p class="m-0 grid min-w-0 gap-1">
      <span class={LABEL}>{label}</span>
      <span class="watch-digest grid font-code text-small leading-snug">
        {watching.DIGEST_LINES.map((line, row) => (
          <span class="whitespace-nowrap">
            {[...line].map((digit, column) => {
              const shown = row * line.length + column < digits.revealed
              return <span class={shown ? (digits.matched ? 'font-bold text-ink' : 'text-quiet') : 'text-quiet opacity-15'}>{digit}</span>
            })}
          </span>
        ))}
      </span>
    </p>
  )
}

/**
 * Draws the recording's presses, one byte a step, each as the Game Boy's pad,
 * those played in ink and the rest faint, the one playing ringed in the
 * agent's Denim.
 */
export function drawPresses(step: number) {
  return watching.RECORDING.slice(1).map((each, n) => (
    <span
      aria-hidden="true"
      class={['watch-press grid aspect-square place-items-center rounded-1 border-ring', n + 1 === step ? 'border-denim-mark' : 'border-transparent', n + 1 <= step ? 'text-ink' : 'text-quiet opacity-40']}
      innerHTML={padMark(each.press)}
    />
  ))
}

/**
 * Draws the check before a press plays at `t`, the intro's state against the
 * run's digest, the run's digits beside those the intro writes.
 */
export function drawBefore(t: number) {
  const digits = watching.digitsAt(t)
  return (
    <section class="watch-before grid content-start gap-2">
      <p class={[LABEL, 'm-0']}>{WORDS.before}</p>
      {drawCheck('Digest', watching.introAt(t))}
      <div class="grid grid-cols-2 gap-3 pt-1">
        {drawDigest(WORDS.record, { matched: digits.matched, revealed: watching.RUN.digest.length })}
        {drawDigest(WORDS.intro, digits)}
      </div>
    </section>
  )
}

/**
 * Draws the check once the last press plays at `t`, the return the run recorded
 * beside the one the playback reaches at `step`, and the line the log writes
 * once they match.
 */
export function drawAfter(t: number, step: number) {
  const recorded = watching.returned(watching.RECORDING.at(-1)!.total)
  return (
    <section class="watch-after grid content-start gap-2">
      <p class={[LABEL, 'm-0']}>{WORDS.after}</p>
      {drawCheck('Return', watching.endingAt(t))}
      <Chip class="watch-figure w-full" name="Recorded" value={recorded} />
      <Chip class="watch-figure w-full" name="Reached" role="agent" value={watching.returned(watching.RECORDING[step]!.total)} />
      <p class={[DETAIL, 'm-0 text-ink', watching.loggedAt(t) ? '' : 'invisible']}>
        {`The playback reached the return of ${recorded} the run recorded`}
      </p>
    </section>
  )
}
