import { type VNode, defineComponent } from 'vue'

import * as faces   from '../../../lib/identity/faces.ts'
import { IDENTITY } from '../../../lib/identity/identity.ts'

/**
 * The classes laying out each part of the widget: a face's group, the strip
 * naming it, its swatches and one swatch, and the parts it sets.
 */
const PARTS = {
  group    : 'grid gap-3',
  parts    : 'grid gap-4 px-4',
  strip    : 'identity-strip flex flex-wrap items-center justify-between gap-x-4 gap-y-2 rounded-2 bg-lift py-2 pr-2 pl-4',
  swatch   : 'identity-face focus-ring grid cursor-pointer justify-items-center gap-0 rounded-1 bg-ground pt-1 pb-1 text-ink disabled:cursor-default',
  swatches : 'flex flex-wrap gap-1'
}

/**
 * The faces' state, as `useFaces` holds it.
 */
type Faces = ReturnType<typeof faces.useFaces>

/**
 * The style setting text in `role`'s face at `weight`.
 */
function styleOf(role: faces.Role, weight: faces.Weight) {
  return { fontFamily: IDENTITY.faces[role].stack, fontStyle: weight.italic ? 'italic' : 'normal', fontWeight: weight.weight }
}

/**
 * Stacks the code face's copies of the setting's name a paragraph names at
 * each of its weights, the copy at `at` alone shown.
 */
function drawInline(at: number) {
  return (
    <span class="identity-inline inline-grid">
      {faces.WEIGHTS.code.map((weight, n) => <code aria-hidden={n !== at} data-shown={n === at} style={styleOf('code', weight)}>{faces.WORDS.inline}</code>)}
    </span>
  )
}

/**
 * Draws the part `role`'s face sets at `weight`, the code face's weight `code`
 * setting the name inside the body's paragraph.
 */
function drawPart(role: faces.Role, weight: faces.Weight, code: number): VNode {
  const style = styleOf(role, weight)
  if (role === 'display') return <div class="text-title leading-tight" style={style}>{faces.WORDS.head}</div>
  if (role === 'body') return <div class="text-body leading-normal" style={style}>{faces.WORDS.lead}{drawInline(code)}{faces.WORDS.tail}</div>
  return <div class="flex flex-wrap gap-x-5 text-figure tabular-nums" style={style}>{faces.WORDS.figures.map(each => <span>{each}</span>)}</div>
}

/**
 * Stacks the copies of the part `role`'s face sets that `copiesOf` lays out
 * over a hidden copy at the heaviest weight, which holds the part's size as
 * the shown copy changes, Literata's upright copy moving along its weight axis
 * and every other change crossfading.
 */
function drawStack({ at }: Faces, role: faces.Role) {
  const heaviest = faces.WEIGHTS[role].reduce((most, each) => each.weight > most.weight ? each : most)

  return (
    <div class="identity-stack grid min-w-0">
      <div aria-hidden="true" class="invisible">{drawPart(role, heaviest, at.code)}</div>
      {faces.copiesOf(role, at[role]).map(({ shown, weight }) => (
        <div aria-hidden={!shown} class="identity-copy" data-shown={shown}>{drawPart(role, weight, at.code)}</div>
      ))}
    </div>
  )
}

/**
 * Draws the strip naming `role`'s face in its own letters beside what it sets,
 * and its weights as swatches setting Ag in each.
 */
function drawStrip({ choices }: Faces, role: faces.Role) {
  const face   = IDENTITY.faces[role]
  const choice = choices[role]

  return (
    <div class={PARTS.strip}>
      <div class="identity-name flex min-w-0 flex-wrap items-baseline gap-x-3">
        <span class="text-say leading-tight font-medium text-ink" style={{ fontFamily: face.stack }}>{face.family}</span>
        <span class="font-body text-small text-quiet">{face.purpose}</span>
      </div>
      <div {...choice.root.value} aria-label={`${face.family}’s weights`} class={PARTS.swatches}>
        {faces.WEIGHTS[role].map(weight => (
          <button
            {...choice.item(weight.label)}
            aria-label={`${face.family}, ${weight.italic ? 'italic' : `weight ${weight.label}`}`}
            class={PARTS.swatch}
            disabled={faces.WEIGHTS[role].length === 1}
            type="button"
          >
            <span aria-hidden="true" class="text-say leading-tight" style={styleOf(role, weight)}>Ag</span>
            <span class="identity-weight font-code text-label font-medium text-quiet tabular-nums">{weight.label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

/**
 * Each face the identity declares under a strip naming it in its own letters
 * beside what it sets, its weights as swatches setting Ag in each, and the
 * parts of a page it sets, a heading, a paragraph naming a setting in code,
 * and figures, a press on a swatch setting every part that face sets at its
 * weight, gliding where the face loads its weight axis as a range and
 * crossfading otherwise.
 */
export const IdentityFaces = defineComponent({
  name  : 'IdentityFaces',
  setup : () => {
    const state = faces.useFaces()
    return () => (
      <div class="grid gap-5">
        {faces.ROLES.map(role => (
          <section class={PARTS.group}>
            {drawStrip(state, role)}
            <div class={PARTS.parts}>{drawStack(state, role)}</div>
          </section>
        ))}
      </div>
    )
  }
})
