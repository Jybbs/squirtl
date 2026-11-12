import { defineComponent, ref } from 'vue'

import { type Scheme, type Token, hexOf, IDENTITY } from '../../../lib/identity/identity.ts'
import { GROUNDS, SCHEMES }                         from '../../../lib/identity/palette.ts'
import * as seam                                    from '../../../lib/identity/seam.ts'
import { blocksOf, viewBoxOf }                      from '../../../lib/marks/drawings.ts'
import { dotRadius, paintOf }                       from '../../../lib/marks/logo.ts'
import { DETAIL, LABEL, SCRUB_PARTS }               from '../kit/widget.ts'

/**
 * The opacity a dot of the trail the fill has not reached stands at.
 */
const UNLIT = 0.12

/**
 * The seam's state, as `useSeam` holds it.
 */
type Seam = ReturnType<typeof seam.useSeam>

/**
 * Draws the logo on `scheme`'s ground, every dot the fill has not reached past
 * `at` faded.
 */
function drawMark(scheme: Scheme, at: number) {
  return (
    <svg aria-hidden="true" class="block h-auto w-full" viewBox={viewBoxOf(seam.MARK.view)}>
      {seam.MARK.dots.map(dot => (
        <circle class="identity-dot" cx={dot.x} cy={dot.y} fill={paintOf(dot, scheme)} opacity={seam.FILLED.indexOf(dot) > at ? UNLIT : 1} r={dotRadius} />
      ))}
      <g innerHTML={blocksOf(seam.MARK, scheme)} shape-rendering="crispEdges" />
    </svg>
  )
}

/**
 * Draws the strip reading LIGHT and DARK on either side of the seam, its
 * handle at the seam, which a reader drags to move it.
 */
function drawStrip({ strip }: Seam) {
  return (
    <div {...strip.root.value} class="relative">
      <div {...strip.control.value} class={[SCRUB_PARTS.control, 'identity-strip-bar relative h-7 overflow-hidden rounded-2 select-none']}>
        {SCHEMES.map(scheme => (
          <span
            aria-hidden="true"
            class="identity-side absolute inset-0 flex items-center px-3 font-code text-label font-medium tracking-caps uppercase"
            data-scheme={scheme}
            style={{ background: GROUNDS[scheme].hex, color: hexOf(IDENTITY.logo[scheme].thirds.at(-1) as Token) }}
          >
            {scheme}
          </span>
        ))}
        <span aria-hidden="true" class="identity-handle absolute inset-y-0 flex items-center justify-center gap-0 bg-primary font-code text-label text-athens-gray">
          <span>◀</span><span>▶</span>
        </span>
      </div>
      <div {...strip.thumb.value} class={[SCRUB_PARTS.thumb, 'absolute inset-0 rounded-2']} />
    </div>
  )
}

/**
 * Draws the range stepping the trail dot by dot.
 */
function drawTrail({ fill, last, trail }: Seam) {
  const along = `${100 * fill.value / last}%`

  return (
    <div {...trail.root.value} class="relative">
      <div {...trail.control.value} class={[SCRUB_PARTS.control, 'relative h-6 select-none']}>
        <span class="absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-rule" />
        <span class="absolute top-1/2 left-0 h-1 -translate-y-1/2 rounded-full bg-denim-mark" style={{ width: along }} />
      </div>
      <div {...trail.thumb.value} class={[SCRUB_PARTS.thumb, 'absolute top-1/2 size-4 -translate-1/2 rounded-full border-ring border-lift bg-denim-mark']} style={{ left: along }} />
    </div>
  )
}

/**
 * Draws each ground's key to the trail, the entry whose color the dot the fill
 * stands on takes ringed.
 */
function drawKeys({ lit }: Seam) {
  return (
    <div class="identity-keys grid gap-4">
      {SCHEMES.map(scheme => (
        <div class="grid gap-1">
          <span class={LABEL}>{scheme} ground</span>
          <ol class="identity-key grid gap-1">
            {seam.keyOf(scheme).map(entry => (
              <li class="identity-entry grid items-center gap-x-2 rounded-1 px-2 py-1" data-on={entry.hex === lit.value[scheme]}>
                <span aria-hidden="true" class="identity-trail-dot row-span-2 size-4 rounded-full" style={{ background: entry.hex }} />
                <span class="text-small">{entry.what}</span>
                <span class={DETAIL}>{entry.name} {entry.hex}</span>
              </li>
            ))}
          </ol>
        </div>
      ))}
    </div>
  )
}

/**
 * The logo on both grounds at once, the dark one laid over the light from the
 * seam rightward, under a strip reading LIGHT and DARK a reader drags to move
 * the seam and over a range stepping the trail dot by dot, each ground's key
 * marking the color of the dot the fill stands on.
 */
export const IdentityLogo = defineComponent({
  name  : 'IdentityLogo',
  setup : () => {
    const box   = ref<HTMLElement>()
    const state = seam.useSeam(box)

    return () => (
      <div class="identity-seam @container grid gap-3" ref={box} style={{ '--seam': `${state.at.value}%` }}>
        <div class="flex justify-end">
          <span class={[DETAIL, 'flex-none']}>{state.at.value} · {seam.SEAM - 1 - state.at.value}</span>
        </div>
        {drawStrip(state)}
        <div class="relative overflow-hidden rounded-2">
          {SCHEMES.map(scheme => <div class="identity-ground-mark p-3" data-scheme={scheme} style={{ background: GROUNDS[scheme].hex }}>{drawMark(scheme, state.fill.value)}</div>)}
          <span aria-hidden="true" class="identity-seam-line absolute inset-y-0 bg-primary" />
        </div>
        {drawTrail(state)}
        {drawKeys(state)}
      </div>
    )
  }
})
