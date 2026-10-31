import { type PropType, defineComponent } from 'vue'

import { type KeyEntry, type KeyFigures, hueOf } from '../../../lib/widgets/chips.ts'
import { fromMouse }                             from '../../../lib/widgets/scrub.ts'
import { Chip }                                  from './chip.tsx'
import { HUES }                                  from './hues.ts'
import { LABEL, SWATCH }                         from './widget.ts'

/**
 * The classes inking one entry of the strip: its mark, its name, and the ground
 * and ring it takes while it is lit.
 */
interface StripTint {
  lit  : string
  mark : string
  name : string
}

/**
 * The column each of an entry's two figures and their heads takes, each class
 * written whole so the theme's scan finds it.
 */
const COLUMNS = ['col-start-2', 'col-start-3'] as const

/**
 * The classes laying out each part of a key: an entry's chip beside its
 * figures, which takes a row of its own below the widget's 40rem, a figure and
 * its head, the label in capitals over the key, the grid of entries and their
 * figures, and the key itself.
 */
const PARTS = {
  chip    : 'col-start-1 @max-sm:col-span-3',
  figure  : 'text-right font-code text-figure leading-none font-medium whitespace-nowrap text-ink '
          + 'tabular-nums',
  figures : 'key-figures grid items-center gap-x-4 gap-y-2',
  head    : 'text-right whitespace-nowrap',
  label   : LABEL,
  root    : 'grid content-start gap-2'
}

/**
 * The classes laying out the strip a key without figures draws, one row of
 * entries that wraps where the column runs short, each entry its mark in a well
 * of the mark's size, or a swatch where it has none, its name in capitals, and
 * its value, the entry a reader lights ringed in its hue while the rest dim,
 * and what it records read out to a screen reader alone.
 */
const STRIP_PARTS = {
  art    : '*:size-key-mark',
  dim    : 'opacity-45',
  entry  : 'inline-flex items-center gap-2 rounded-2 border-hairline border-transparent py-1 pr-2 pl-1 '
         + 'text-left motion-safe:transition-opacity',
  list   : 'key-strip flex flex-wrap gap-x-3 gap-y-1',
  mark   : 'grid size-key-mark flex-none place-items-center',
  name   : 'font-code text-label leading-snug font-semibold tracking-caps whitespace-nowrap uppercase',
  swatch : SWATCH,
  told   : 'visually-hidden',
  value  : 'font-code text-small leading-snug font-medium whitespace-nowrap text-ink tabular-nums'
}

/**
 * The classes inking an entry that takes no hue.
 */
const UNTINTED: StripTint = { lit: 'border-rule bg-lift', mark: 'text-quiet', name: 'text-ink' }

/**
 * Reads what the chip of `entry` shows, leaving out the name a screen reader
 * reads and the figures, which the key sets beside the chip.
 */
const chipOf = ({ hue, mark, name, note, role, value }: KeyEntry) => ({ hue, mark, name, note, role, value })

/**
 * Draws the parts of one entry of the strip in `tint`: its mark, or a swatch
 * where it has none, its name, its value where it takes one, and what it
 * records, read out to a screen reader alone.
 */
function stripParts(entry: KeyEntry, tint: StripTint) {
  const well = [STRIP_PARTS.mark, tint.mark]

  return [
    entry.mark
      ? <span aria-hidden="true" class={[well, STRIP_PARTS.art]} innerHTML={entry.mark} />
      : <span aria-hidden="true" class={well}><span class={STRIP_PARTS.swatch} /></span>,
    <span class={[STRIP_PARTS.name, tint.name]}>{entry.name}</span>,
    entry.value === undefined || entry.value === null
      ? null
      : <span class={STRIP_PARTS.value}>{entry.value}</span>,
    entry.note ? <span class={STRIP_PARTS.told}>, {entry.note}</span> : null
  ]
}

/**
 * Reads the classes inking `entry` in the strip, from the hue it takes or the
 * hue of its role.
 */
function stripTintOf(entry: KeyEntry): StripTint {
  const named = hueOf(entry)
  if (named === null) return UNTINTED
  const { ground, ink, ring, text } = HUES[named]
  return { lit: `${ring} ${ground}`, mark: ink, name: text }
}

/**
 * The site's one key, the legend every widget names its players, its terms, and
 * its marks through, under the label it takes. Where the key is given `heads`,
 * each entry is a chip beside the two figures it records under them, and
 * otherwise the entries form one strip of marks and names, where the entry
 * `lit` names stays lit while the rest dim. Where the key is `pressable`,
 * each entry of the strip is a button reporting a mouse resting on it through
 * `hover` and a press through `press`, the one `pressed` names marked pressed.
 */
export const Key = defineComponent({
  emits : ['hover', 'press'],
  name  : 'Key',

  props: {
    entries   : { required: true, type: Array as PropType<readonly KeyEntry[]> },
    heads     : { default: null, type: Array as unknown as PropType<KeyFigures | null> },
    label     : { default: null, type: String as PropType<string | null> },
    lit       : { default: null, type: Number as PropType<number | null> },
    pressable : { default: false, type: Boolean },
    pressed   : { default: null, type: Number as PropType<number | null> }
  },

  setup: (props, { emit }) => {
    const figured = (heads: KeyFigures) => [
      <span class={PARTS.chip} />,
      ...heads.map((head, column) => <span class={[PARTS.label, PARTS.head, COLUMNS[column]]}>{head}</span>),
      ...props.entries.flatMap(each => [
        <span class={PARTS.chip}><Chip class="w-full" {...chipOf(each)} /></span>,
        ...(each.figures ?? []).map((figure, column) => (
          <span class={[PARTS.figure, COLUMNS[column]]}>{figure}</span>
        ))
      ])
    ]

    const dimmed = (n: number) => props.lit !== null && props.lit !== n ? STRIP_PARTS.dim : null

    const entryOf = (entry: KeyEntry, n: number) => {
      const tint  = stripTintOf(entry)
      const style = [STRIP_PARTS.entry, props.lit === n ? tint.lit : null, dimmed(n)]
      return props.pressable
        ? (
            <li key={entry.name}>
              <button
                aria-label={entry.label}
                aria-pressed={props.pressed === n}
                class={['focus-ring', style]}
                onClick={() => emit('press', n)}
                onPointerenter={(event: PointerEvent) => { if (fromMouse(event)) emit('hover', n) }}
                onPointerleave={() => emit('hover', null)}
                type="button"
              >
                {stripParts(entry, tint)}
              </button>
            </li>
          )
        : <li class={style} key={entry.name}>{stripParts(entry, tint)}</li>
    }

    return () => (
      <div class={PARTS.root}>
        {props.label === null ? null : <span class={PARTS.label}>{props.label}</span>}
        {props.heads === null
          ? (
              <ul class={STRIP_PARTS.list}>
                {props.entries.map((each, n) => entryOf(each, n))}
              </ul>
            )
          : <div class={PARTS.figures}>{figured(props.heads)}</div>}
      </div>
    )
  }
})
