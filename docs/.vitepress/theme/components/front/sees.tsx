import { type Ref, type VNode, defineComponent, ref } from 'vue'

import * as sees        from '../../../lib/front/sees.ts'
import * as labels      from '../../../lib/front/sees/labels.ts'
import * as playthrough from '../../../lib/front/sees/playthrough.ts'
import { SCREEN }       from '../../../lib/game/screen.ts'
import type { Canvas }  from '../../../lib/widgets/frames.ts'
import { stepText }     from '../../../lib/widgets/numbers.ts'
import type { Scrub }   from '../../../lib/widgets/scrub.ts'
import { Chip }         from '../kit/chip.tsx'
import * as widget      from '../kit/widget.ts'

/**
 * The classes every drawing of the widget shares, which scale it to its column
 * and ring it in the rule with its pixels drawn square.
 */
const ART = 'sees-art pixelated block h-auto w-full rounded-1'

/**
 * The classes of the tag naming the step of each gray frame, set over the
 * frame's bottom left corner.
 */
const TAG = 'col-start-1 row-start-1 self-end justify-self-start whitespace-nowrap rounded-tr-1 '
          + 'rounded-bl-1 bg-ground p-1 font-code text-label leading-none font-medium text-ink'

/**
 * The shape and the bytes of each entry of the observation, beneath its
 * drawing.
 */
const captions = labels.captionsOf()

/**
 * Each event flag beside the mark of the term it pays, in the order the network
 * reads them.
 */
const flags = labels.flagsOf()

/**
 * Each gray frame from the oldest, the steps it lies back from the newest
 * beside its name for a screen reader and the tag set over it.
 */
const names = labels.frameNamesOf()

/**
 * Draws the caption `label` beside `figure` in the grid area the class `place`
 * names, laid out by the classes `layout`, by default `label` above `figure`.
 */
function captionOf(
  figure : string,
  label  : string,
  place  : string,
  layout : string = 'grid content-start gap-sees-seam'
): VNode {
  return (
    <div class={[place, layout]}>
      <span class={widget.LABEL}>{label}</span>
      <span class={widget.DETAIL}>{figure}</span>
    </div>
  )
}

/**
 * Draws a canvas `width` by `height` pixels, named `label` for a screen reader
 * and set in place by the classes `place`.
 */
function drawingOf(
  canvas : Canvas,
  label  : string,
  place  : string,
  width  : number,
  height : number = width
): VNode {
  return (
    <canvas aria-label={label} class={[ART, place]} height={height} ref={canvas} role="img" width={width} />
  )
}

/**
 * Draws the gray frames as one block of the screen's shape, the oldest first,
 * which serves as the slider over the episode's steps.
 */
function frameStripOf(frames: readonly Canvas[], scrub: Scrub): VNode {
  const { height, width } = sees.OBSERVING.frame
  return (
    <div {...scrub.root.value} class="sees-frames">
      <div {...scrub.control.value} class={[widget.SCRUB_PARTS.control, 'grid']}>
        <div class="col-start-1 row-start-1 grid grid-cols-2 gap-sees-seam">
          {names.map((name, i) => (
            <div class="grid" key={name.back}>
              {drawingOf(frames[i]!, name.label, 'col-start-1 row-start-1', width, height)}
              <span aria-hidden="true" class={TAG}>{name.tag}</span>
            </div>
          ))}
        </div>
        <span
          {...scrub.thumb.value}
          class={[widget.SCRUB_PARTS.thumb, 'col-start-1 row-start-1 rounded-1']}
        />
      </div>
    </div>
  )
}

/**
 * Draws the screen, the gray frames, and the grid at one height above their
 * captions, and the flags' chips beneath, each set chip in its term's hue.
 */
function viewOf(root: Ref<HTMLElement | undefined>, scrub: Scrub, stage: playthrough.Playthrough): VNode {
  const flagged = stage.flagged.value
  const player  = 'The game screen as a player sees it'
  const reached = 'The squares Blue has reached on this map, Blue at the center'
  const row     = 'flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1'
  return (
    <div class="@container" ref={root}>
      <div class="sees grid gap-x-4 gap-y-3">
        {drawingOf(stage.screen, player, 'sees-screen', SCREEN.width, SCREEN.height)}
        {frameStripOf(stage.frames, scrub)}
        {drawingOf(stage.grid, reached, 'sees-grid', sees.OBSERVING.grid)}
        {captionOf(stepText(stage.step.value, stage.last), 'What a player sees', 'sees-screen-say')}
        {captionOf(captions.frames, 'Frames', 'sees-frames-say')}
        {captionOf(captions.grid, 'Grid', 'sees-grid-say')}
        <div class="sees-flags mt-2 grid gap-2">
          {captionOf(captions.flags, 'Flags', '', row)}
          <div class="grid grid-cols-1 gap-2 @sm:grid-cols-2 @lg:grid-cols-4">
            {flags.map((each, i) => (
              <Chip
                class="w-full"
                key={each.flag}
                mark={each.mark}
                name={each.name}
                role={flagged[i] ? each.term : 'none'}
                value={flagged[i] ? '1' : '0'}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * The front page's widget showing what the network sees in place of Blue's
 * coordinates beside the game screen, set to a step by a press or a drag along
 * the gray frames or the arrow keys, and held at its step by a mouse resting on
 * them.
 */
export const StorySees = defineComponent({
  name  : 'StorySees',
  setup : () => {
    const root             = ref<HTMLElement>()
    const { scrub, stage } = playthrough.usePlaythrough(root)

    return () => viewOf(root, scrub, stage)
  }
})
