import { defineComponent } from 'vue'

import { spriteMarkup }                              from '../../../lib/drawing/sprites.ts'
import { type Hue, type Scheme, IDENTITY, contrast } from '../../../lib/identity/identity.ts'
import * as palette                                  from '../../../lib/identity/palette.ts'
import { usePalette }                                from '../../../lib/identity/picking.ts'
import { fixed }                                     from '../../../lib/widgets/numbers.ts'
import { LABEL }                                     from '../kit/widget.ts'

/**
 * The classes laying out each part of the widget: a band and its words, a row
 * of bands, a ground's row of the ramp and its steps, and the card naming the
 * color or the step picked and one of its meters.
 */
const PARTS = {
  band    : 'identity-band focus-ring relative min-w-0 cursor-pointer overflow-hidden',
  bands   : 'identity-bands flex overflow-hidden rounded-2',
  card    : 'identity-card grid gap-3 rounded-2 border-hairline border-rule bg-lift p-4',
  ground  : 'identity-ground grid items-center gap-3 rounded-2 px-3 py-1',
  meter   : 'identity-meter grid items-center gap-2',
  step    : 'identity-step focus-ring h-6 cursor-pointer rounded-1 font-code text-label font-medium',
  steps   : 'identity-steps grid gap-1',
  verdict : 'identity-verdict rounded-2 px-2 py-1 text-center font-code text-label font-medium tracking-caps uppercase',
  words   : 'identity-words absolute right-2 bottom-2 left-2 grid gap-0 text-left whitespace-nowrap'
}

/**
 * What a meter's verdict reads for each level of contrast.
 */
const VERDICTS: Readonly<Record<palette.Level, string>> = { fill: 'Fill only', mark: 'Mark', text: 'Text' }

/**
 * The palette's state, as `usePalette` holds it.
 */
type Palette = ReturnType<typeof usePalette>

/**
 * Places a contrast ratio along a meter, as a share of its width.
 */
const along = (ratio: number) => `${(100 * palette.meterOf(ratio)).toFixed(2)}%`

/**
 * Draws one meter of `hex`'s contrast on `ground`, on a log scale from 1 to 21
 * ticked at the 3:1 a mark needs and the 4.5:1 text needs, its figure and its
 * verdict beside it.
 */
function drawMeter(hex: string, ground: { hex: string, name: string }) {
  const ratio = contrast(hex, ground.hex)
  const level = palette.levelOf(ratio)

  return (
    <div class={PARTS.meter}>
      <span class={LABEL}>On {ground.name}</span>
      <span class="identity-track relative h-2 rounded-2">
        <span class="identity-fill block h-full rounded-2 bg-ink" style={{ width: along(ratio) }} />
        {[3, 4.5].map(tick => <span aria-hidden="true" class="identity-tick absolute bg-quiet" style={{ left: along(tick) }} />)}
      </span>
      <span class="text-right font-code text-small font-medium tabular-nums">{fixed(ratio, 2)}:1</span>
      <span class={PARTS.verdict} data-level={level}>{VERDICTS[level]}</span>
    </div>
  )
}

/**
 * Draws Blue in `hue`'s ramp on `scheme`'s ground.
 */
function drawBlue(hue: Hue, scheme: Scheme) {
  const markup = spriteMarkup(IDENTITY.sprites.player.frames[0]!, { fills: palette.blueFills(hue, scheme), size: 1, x: 0, y: 0 })

  return <svg aria-hidden="true" class="size-6" innerHTML={markup} shape-rendering="crispEdges" viewBox="0 0 16 16" />
}

/**
 * Draws every named color as a band in its table's row, the band picked
 * widening to name itself and its hex.
 */
function drawBands({ bands, color }: Palette) {
  return (
    <div {...bands.root.value} aria-label="The palette" class="grid gap-3">
      {palette.TABLES.map(({ table, title }) => (
        <div class="grid gap-1" data-open={color.value.table === table}>
          <span class={LABEL}>{title}</span>
          <div class={PARTS.bands}>
            {palette.NAMED.filter(each => each.table === table).map(each => (
              <button {...bands.item(each.token)} aria-label={`${each.name}, ${each.hex}`} class={PARTS.band} style={{ background: each.hex, color: palette.inkOn(each.hex) }} type="button">
                <span class={PARTS.words}>
                  <span class="font-display text-small font-medium">{each.name}</span>
                  <span class="font-code text-label font-medium">{each.hex}</span>
                </span>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

/**
 * Draws the ramp of `hue` on `scheme`'s ground, Blue drawn in it beside the
 * ground's name and a button for each step.
 */
function drawGround({ color, steps }: Palette, hue: Hue, scheme: Scheme) {
  const ground = palette.GROUNDS[scheme]

  return (
    <div class={PARTS.ground} style={{ background: ground.hex, color: palette.inkOn(ground.hex) }}>
      {drawBlue(hue, scheme)}
      <span class="font-code text-label font-medium tracking-caps uppercase">{ground.name}</span>
      <span class={PARTS.steps}>
        {palette.stepsOf(hue, scheme).map((each, n) => (
          <button
            {...steps.item(`${scheme}-${n}` as palette.Picked)}
            aria-label={`${color.value.name} ${each.name} on ${ground.name}, ${each.hex}`}
            class={PARTS.step}
            style={{ background: each.hex, color: palette.inkOn(each.hex) }}
            type="button"
          >
            {n < 4 ? n + 1 : 'T'}
          </button>
        ))}
      </span>
    </div>
  )
}

/**
 * Draws the picked color's ramp on both grounds, or a line saying it carries
 * none.
 */
function drawRamp(state: Palette) {
  const { color, hue, steps } = state
  if (hue.value === null) {
    return <span class="self-center text-small text-quiet">{color.value.name} carries no ramp, so it stands alone in both schemes.</span>
  }

  return (
    <div {...steps.root.value} aria-label={`${color.value.name}’s ramp`} class="grid gap-1">
      {palette.SCHEMES.map(scheme => drawGround(state, hue.value!, scheme))}
    </div>
  )
}

/**
 * Draws the card naming what `shown` names beside its contrast on each ground.
 */
function drawCard(shown: palette.Shown) {
  return (
    <div aria-live="polite" class={PARTS.card}>
      <span aria-hidden="true" class="identity-swatch rounded-1" style={{ background: shown.hex }} />
      <div class="grid min-w-0 gap-1">
        <div class="flex flex-wrap items-baseline gap-x-2 font-semibold">{shown.name} <span class="font-code text-small text-quiet">{shown.what}</span></div>
        <span class="font-code text-small tabular-nums">{shown.hex}</span>
      </div>
      <div class="identity-meters grid gap-2">{palette.SCHEMES.map(scheme => drawMeter(shown.hex, palette.GROUNDS[scheme]))}</div>
    </div>
  )
}

/**
 * Every color the identity names as a band in its table's row, the band picked
 * widening to name itself and its hex, a hue's ramp opening beneath on both
 * grounds with Blue drawn in it, and a card naming the color or the step
 * picked beside its contrast on each ground.
 */
export const IdentityPalette = defineComponent({
  name  : 'IdentityPalette',
  setup : () => {
    const state = usePalette()
    return () => (
      <div class="@container grid gap-4">
        {drawBands(state)}
        <div class="identity-ramp grid gap-1">{drawRamp(state)}</div>
        {drawCard(state.shown.value)}
      </div>
    )
  }
})
