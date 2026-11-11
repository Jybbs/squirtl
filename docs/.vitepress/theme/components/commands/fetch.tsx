import { defineComponent, reactive, ref } from 'vue'

import * as fetch                 from '../../../lib/commands/fetch.ts'
import { TAG, megabytes, timeOf } from '../../../lib/commands/release.ts'
import { useAutoplay }            from '../../../lib/widgets/autoplay.ts'
import { useChoice }              from '../../../lib/widgets/choice.ts'
import { DETAIL, LABEL }          from '../kit/widget.ts'

/**
 * The classes laying out each part of the widget: the bar its download fills
 * and the fill, a digest's digits, an option of the release and the group of
 * them, a run of the selection and the list of them, and the line spelling
 * what the fetch does.
 */
const PARTS = {
  bar     : 'relative h-1 overflow-hidden rounded-1 bg-rule',
  digits  : 'flex flex-wrap gap-x-2 font-code text-small leading-normal tabular-nums',
  fill    : 'absolute inset-0 origin-left bg-forest-mark motion-safe:transition-transform',
  option  : 'fetch-option rounded-1 border-hairline border-rule px-3 py-1 text-small text-quiet enabled:cursor-pointer focus-ring',
  options : 'flex flex-wrap gap-2',
  run     : 'flex items-center gap-2 font-code text-small tabular-nums',
  runs    : 'fetch-runs flex flex-wrap gap-x-4 gap-y-1',
  verdict : 'fetch-verdict grid border-l-bar pl-3 font-code text-small leading-snug wrap-anywhere',
  window  : '@container grid gap-4 rounded-2 border-hairline border-rule bg-lift p-4'
}

/**
 * The classes of a digit by where it stands in the comparison: Forest where
 * all three digests agree, and ink in bold over a Brick Red rule where one
 * differs, since Brick Red holds a mark's contrast on either ground and not
 * a text's.
 */
const AGREEMENT: Record<fetch.Agreement, string> = {
  agree  : 'bg-forest-1 text-forest-text',
  differ : 'fetch-differ font-bold text-ink',
  open   : 'text-quiet'
}

/**
 * The classes of a run's name and of its swatch by where the run stands, a
 * swatch filled once its run is fetched or refused, ringed while it is
 * fetched, and edged while it waits.
 */
const MARKS: Record<fetch.Mark, { name: string, swatch: string }> = {
  done    : { name: 'text-ink', swatch: 'bg-forest-mark' },
  fail    : { name: 'text-ink', swatch: 'bg-critical' },
  never   : { name: 'text-quiet line-through opacity-45', swatch: 'border-hairline border-quiet' },
  now     : { name: 'text-ink', swatch: 'border-ring border-forest-mark' },
  waiting : { name: 'text-quiet', swatch: 'border-hairline border-quiet' }
}

/**
 * The two states of the release a reader chooses between.
 */
const RELEASES = ['packed', 'altered'] as const

/**
 * The name of each state of the release.
 */
const NAMES: Record<typeof RELEASES[number], string> = {
  altered : `The tar of ${timeOf(fetch.ALTERED.name)} altered`,
  packed  : 'The release as packed'
}

/**
 * Draws the digits of the digest `source` names, its two halves of thirty-two
 * wrapping apart on a narrow column.
 */
function drawDigits(fetching: fetch.Fetching, source: fetch.Source) {
  const digits = fetching.digits(source)
  const half   = digits.length / 2

  return (
    <span class={PARTS.digits}>
      {[digits.slice(0, half), digits.slice(half)].map(part => (
        <span class="whitespace-nowrap">
          {part.map(({ agreement, digit }) => <span class={AGREEMENT[agreement]}>{digit}</span>)}
        </span>
      ))}
    </span>
  )
}

/**
 * Lists the runs the selection matches, each marked by where it stands.
 */
function drawRuns(fetching: fetch.Fetching) {
  const marks = fetching.marks()

  return (
    <ol class={PARTS.runs}>
      {fetch.MATCHED.map((each, i) => (
        <li class={[PARTS.run, MARKS[marks[i]!].name]}>
          <span aria-hidden="true" class={['size-swatch rounded-swatch', MARKS[marks[i]!].swatch]} />
          <span>{timeOf(each.name)}</span>
        </li>
      ))}
    </ol>
  )
}

/**
 * Draws the run being fetched, its name, how much of its tar has arrived, and
 * its three digests.
 */
function drawRun(fetching: fetch.Fetching) {
  const { run, share } = fetching

  return (
    <div class="grid min-w-0 gap-2">
      <div class="flex flex-wrap items-baseline justify-between gap-x-3">
        <span class="font-code text-small">{run.name}</span>
        <span class={DETAIL}>{megabytes(run.megabytes * share)} of {megabytes(run.megabytes)}</span>
      </div>
      <div aria-hidden="true" class={PARTS.bar}>
        <span class={PARTS.fill} style={{ transform: `scaleX(${share.toFixed(4)})` }} />
      </div>
      {fetch.SOURCES.map(({ name, source }) => (
        <div class="mt-1 grid gap-1">
          <span class={LABEL}>{name}</span>
          {drawDigits(fetching, source)}
        </div>
      ))}
    </div>
  )
}

/**
 * One `squirtl fetch --agent dqn` of the deep Q-network's runs, each tar's
 * three SHA-256 digests compared digit by digit once its download lands: the
 * one the download hashes to, the one GitHub carries for its asset, and the
 * one the manifest records. A reader chooses between the release as packed
 * and one whose tar of a run was altered after packing, so GitHub's digest
 * agrees with the download and the manifest's does not, and the fetch exits
 * there on the error the command prints. The fetch plays on its own once the
 * widget shows.
 */
export const CommandsFetch = defineComponent({
  name  : 'CommandsFetch',
  setup : () => {
    const root     = ref<HTMLElement>()
    const fetching = reactive(new fetch.Fetching())
    const play     = useAutoplay(root, {
      beat    : 40,
      done    : () => fetching.done,
      finish  : () => { fetching.finish() },
      restart : () => { fetching.reset() },
      tick    : () => { fetching.advance() }
    })
    const choice = useChoice(RELEASES, release => {
      fetching.altered = release === 'altered'
      play.replay()
    })

    return () => (
      <div class={PARTS.window} ref={root}>
        <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span class={LABEL}>Release {TAG}</span>
          <span class="font-code text-small">{fetch.COMMAND}</span>
        </div>
        <div class="fetch-check grid gap-4">
          {drawRuns(fetching)}
          {drawRun(fetching)}
        </div>
        <div class={[PARTS.verdict, fetching.failed ? 'border-critical text-ink' : 'border-forest-mark text-quiet']}>
          <span aria-hidden="true" class="invisible">{fetch.LONGEST}</span>
          <span role="status">{fetching.verdict()}</span>
        </div>
        <div {...choice.root.value} aria-label="The release" class={PARTS.options}>
          {RELEASES.map(release => <button {...choice.item(release)} class={PARTS.option}>{NAMES[release]}</button>)}
        </div>
      </div>
    )
  }
})
