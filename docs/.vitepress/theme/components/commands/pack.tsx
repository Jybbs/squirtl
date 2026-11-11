import { defineComponent, reactive, ref } from 'vue'

import * as pack         from '../../../lib/commands/pack.ts'
import { DIGITS }        from '../../../lib/commands/release.ts'
import { useAutoplay }   from '../../../lib/widgets/autoplay.ts'
import { DETAIL, LABEL } from '../kit/widget.ts'

/**
 * The dots a line shows in place of a digest until its tar is written.
 */
const UNWRITTEN = '·'.repeat(DIGITS)

/**
 * Draws the lines of `manifest.json` the window shows as `packing` stands,
 * each digest filled once its tar is written.
 */
function drawLines(packing: pack.Packing) {
  return pack.LINES.slice(packing.first, packing.first + pack.WINDOW).map(line => {
    const written = line.tar !== undefined && packing.packed(line.tar)

    return (
      <span class={['block wrap-anywhere', written && 'text-ink']}>
        {line.text}
        {line.tar === undefined ? null : [
          <span class={written ? 'text-forest-text' : undefined}>{written ? line.tar.sha256 : UNWRITTEN}</span>,
          '"'
        ]}
      </span>
    )
  })
}

/**
 * One `squirtl pack` as the `manifest.json` it writes beside the tars, every
 * line standing from the start and each tar's digest filling once the tar is
 * written into `dist/runs/`, the demonstration first and then each trained
 * run, with the lines shown following the tar written last and the file
 * ringed once every tar is written. The pack plays on its own once the widget
 * shows.
 */
export const CommandsPack = defineComponent({
  name  : 'CommandsPack',
  setup : () => {
    const root    = ref<HTMLElement>()
    const packing = reactive(new pack.Packing())

    useAutoplay(root, {
      beat    : 260,
      done    : () => packing.done,
      finish  : () => { packing.finish() },
      restart : () => { packing.reset() },
      tick    : () => { packing.advance() }
    })

    return () => (
      <div class="grid gap-3" ref={root}>
        <div class="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
          <span class={LABEL}>dist/runs/manifest.json</span>
          <span class={DETAIL}>{packing.head()}</span>
        </div>
        <pre class={[
          'overflow-hidden rounded-2 border-ring bg-lift px-3 py-2 font-code text-small leading-normal whitespace-pre-wrap text-quiet',
          packing.done ? 'border-forest-mark' : 'border-rule'
        ]}>
          <code>{drawLines(packing)}</code>
        </pre>
        <div class={[DETAIL, 'wrap-anywhere']} role="status">{packing.log()}</div>
      </div>
    )
  }
})
