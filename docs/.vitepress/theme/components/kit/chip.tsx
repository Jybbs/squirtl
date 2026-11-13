import { type PropType, defineComponent } from 'vue'

import type { Hue, Role } from '../../../lib/identity/identity.ts'
import { hueOf }          from '../../../lib/widgets/chips.ts'
import { HUES }           from './hues.ts'
import { SWATCH }         from './widget.ts'

/**
 * The classes coloring the parts of a chip, its ground and rule, its mark's
 * ring and ink, and its name.
 */
interface Tint {
  chip : string
  mark : string
  name : string
}

/**
 * The classes coloring a chip in no hue, the ink over a tint of it, which the
 * chip's sheet mixes, and the quiet gray.
 */
const NONE: Tint = { chip: 'chip-none border-quiet', mark: 'border-rule text-quiet', name: 'text-ink' }

/**
 * The classes laying out each part of a chip, which every role shares.
 */
const PARTS = {
  chip   : 'inline-flex min-w-0 items-center gap-2 whitespace-nowrap rounded-r-1 border-l-bar '
         + 'pr-chip-end pl-2',
  mark   : 'chip-mark inline-grid size-mark flex-none place-items-center rounded-full border-hairline '
         + 'bg-athens-gray *:size-mark-art *:pixelated',
  name   : 'font-code text-label leading-tight font-semibold tracking-caps uppercase',
  note   : 'font-code text-small leading-tight text-quiet tabular-nums',
  slot   : 'inline-grid size-mark flex-none place-items-center',
  swatch : SWATCH,
  value  : 'ml-auto pl-3 font-code leading-none font-medium tabular-nums'
}

/**
 * The classes sizing a chip, its height and its value, and coloring its value,
 * at full size in the ink or, for a quiet chip, shorter and smaller with its
 * name and value in the quiet gray.
 */
const SIZES = {
  full  : { chip: 'py-chip-block', name: null, value: 'text-body text-ink' },
  quiet : { chip: 'py-chip-quiet-block', name: 'text-quiet', value: 'text-small text-quiet' }
} as const

/**
 * Reads the classes coloring a chip in the hue `hue`, the ground the
 * hue's lightest shade, the rule its mark, the mark ringed in its third shade
 * and inked in its mark, and the name in its text step, or in no hue where
 * `hue` is `null`.
 */
function tintOf(hue: Hue | null): Tint {
  if (hue === null) return NONE
  const { ground, ink, ring, rule, text } = HUES[hue]
  return { chip: `${rule} ${ground}`, mark: `${ring} ${ink}`, name: text }
}

/**
 * The site's one chip family, a tinted tab naming what it marks in the hue its
 * `hue` names or its `role` takes, as a swatch or as the game's own mark in a
 * round tile, then its name, a quiet note, and its value in tabular figures, so
 * a value changing in place moves nothing beside it. A `quiet` chip is shorter,
 * its name and value in the quiet gray.
 */
export const Chip = defineComponent({
  name: 'Chip',

  props: {
    hue   : { default: null, type: String as PropType<Hue | null> },
    mark  : { default: '', type: String },
    name  : { required: true, type: String },
    note  : { default: null, type: String as PropType<string | null> },
    quiet : { default: false, type: Boolean },
    role  : { default: 'none', type: String as PropType<Role | 'none'> },
    value : { default: null, type: String as PropType<string | null> }
  },

  setup: props => () => {
    const tint = tintOf(hueOf(props))
    const size = SIZES[props.quiet ? 'quiet' : 'full']

    return (
      <span class={[PARTS.chip, size.chip, tint.chip]}>
        {props.mark
          ? <span aria-hidden="true" class={[PARTS.mark, tint.mark]} innerHTML={props.mark} />
          : <span aria-hidden="true" class={PARTS.slot}><span class={[PARTS.swatch, tint.mark]} /></span>}
        <span class={[PARTS.name, size.name ?? tint.name]}>{props.name}</span>
        {props.note === null ? null : <span class={PARTS.note}>{props.note}</span>}
        {props.value === null ? null : <span class={[PARTS.value, size.value]}>{props.value}</span>}
      </span>
    )
  }
})
