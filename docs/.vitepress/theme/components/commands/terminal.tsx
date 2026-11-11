import { defineComponent, reactive, ref } from 'vue'

import * as terminal     from '../../../lib/commands/terminal.ts'
import { useAutoplay }   from '../../../lib/widgets/autoplay.ts'
import { DETAIL, LABEL } from '../kit/widget.ts'

/**
 * The classes laying out each part of the window: the bar across its top and
 * its fill, a checkpoint's tick along the bar, the run's status, the window's
 * body, a file's row and its parts, and the prompt pressed to run the next
 * command.
 */
const PARTS = {
  bar    : 'relative h-2 overflow-hidden rounded-1 bg-ground',
  body   : 'grid gap-2 p-4 font-code text-small leading-snug text-ink',
  fill   : 'absolute inset-0 origin-left bg-denim-mark motion-safe:transition-transform',
  name   : 'font-medium',
  prompt : 'flex items-center gap-2 rounded-1 text-left enabled:cursor-pointer enabled:hover:bg-ground focus-ring',
  row    : 'flex flex-wrap gap-x-3 motion-safe:transition-opacity',
  sigil  : 'text-quiet select-none',
  tick   : 'absolute inset-y-0 border-l-hairline border-rule',
  top    : 'grid gap-2 border-b-hairline border-rule p-4',
  window : '@container overflow-hidden rounded-2 border-hairline border-rule bg-lift'
}

/**
 * The share of the run each checkpoint's tick marks along the bar, every one
 * but the run's end.
 */
const TICKS = Array.from({ length: terminal.RUN.steps / terminal.RUN.checkpoint - 1 }, (_, n) =>
  `${(100 * (n + 1) * terminal.RUN.checkpoint / terminal.RUN.steps).toFixed(2)}%`)

/**
 * Lists each file of the run's directory a row each, its name, what it holds
 * as `run` stands, and when the run writes it, a file not yet there dimmed.
 */
function drawFiles(run: terminal.Training) {
  return (
    <ol>
      {run.files().map((file, n) => (
        <li class={[PARTS.row, !file.there && 'opacity-45']}>
          <span aria-hidden="true" class={PARTS.sigil}>{n === terminal.FILES.length - 1 ? '└──' : '├──'}</span>
          <span class={PARTS.name}>{terminal.FILES[n]!.name}</span>
          <span>{file.state}<span class={[LABEL, 'ml-3 normal-case']}># {terminal.FILES[n]!.when}</span></span>
        </li>
      ))}
    </ol>
  )
}

/**
 * One run of `squirtl train` as a terminal window: the run's bar and where it
 * stands across the top, the directory listed a file to a row with what it
 * holds and when it is written, and the next command at the prompt beneath,
 * which runs as it is pressed, `squirtl stop` while the run trains and
 * `squirtl train` once it has ended. The run plays on its own once the window
 * shows, slowing to show its episode's end once the stop file is written.
 */
export const CommandsTerminal = defineComponent({
  name  : 'CommandsTerminal',
  setup : () => {
    const root = ref<HTMLElement>()
    const run  = reactive(new terminal.Training())

    useAutoplay(root, {
      beat    : () => run.stopAt === null ? 120 : 900,
      done    : () => run.ended,
      finish  : () => { while (!run.ended) run.advance() },
      restart : () => { run.reset() },
      rest    : 6000,
      tick    : () => { run.advance() }
    })

    const press = () => run.ended ? run.reset() : run.stop()
    const next  = () => run.ended ? 'squirtl train' : 'squirtl stop'

    return () => (
      <div class={PARTS.window} ref={root}>
        <div class={PARTS.top}>
          <div aria-hidden="true" class={PARTS.bar}>
            <span class={PARTS.fill} style={{ transform: `scaleX(${(run.step / terminal.RUN.steps).toFixed(4)})` }} />
            {TICKS.map(left => <span class={PARTS.tick} style={{ left }} />)}
          </div>
          <p class={DETAIL} role="status">{run.status()}</p>
        </div>
        <div class={PARTS.body}>
          <p><span aria-hidden="true" class={PARTS.sigil}>$ </span><code>squirtl train</code></p>
          <p class="text-quiet">{terminal.RUN.directory}/</p>
          {drawFiles(run)}
          {run.stopAt === null ? null : [
            <p><span aria-hidden="true" class={PARTS.sigil}>$ </span><code>squirtl stop</code></p>,
            <p class="text-quiet">Wrote the stop file ending the run in {terminal.RUN.directory}</p>
          ]}
          <button
            aria-label={run.stopping ? next() : `Run ${next()}`}
            class={PARTS.prompt}
            disabled={run.stopping}
            hidden={run.stopping}
            onClick={press}
            type="button"
          >
            <span aria-hidden="true" class={PARTS.sigil}>$</span>
            <code>{next()}</code>
          </button>
        </div>
      </div>
    )
  }
})
