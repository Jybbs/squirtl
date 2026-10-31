import { defineComponent } from 'vue'

import { PLAYERS }                from '../../../../lib/front/race.ts'
import { type Figures, keyTerms } from '../../../../lib/front/reward.ts'
import { Chip }                   from '../../kit/chip.tsx'
import { Key }                    from '../../kit/key.tsx'
import { DETAIL, LABEL }          from '../../kit/widget.ts'

/**
 * The classes laying out the reward's figures and its key: a list of chips,
 * whose column the sheet holds at least as wide as its widest chip so every
 * value sits inside its chip, the figures, which sit in the climb's upper corner
 * once the climb stands beside the screen, as far from a jump's tile as the tile
 * sits from its dot, the key, and the return so far.
 */
const FIGURES = {
  chips   : 'reward-chips grid gap-2',
  figures : 'reward-chips pointer-events-none mb-4 grid gap-2 @lg:absolute @lg:right-1/6 @lg:left-7 @lg:pr-3 '
          + '@lg:pl-5',
  key     : 'reward-pair mt-3 grid gap-x-6 gap-y-4 border-t-hairline border-rule pt-4',
  total   : 'font-code text-title leading-none font-medium whitespace-nowrap tabular-nums @sm:text-hero'
}

/**
 * The classes hiding a term chip's note, the chip's third part, wherever the
 * figures run too narrow for it: below the widget's 40rem, and from its 60rem,
 * where they sit in the climb's upper corner beside the screen.
 */
const NOTE = '*:nth-3:hidden @sm:*:nth-3:inline @lg:*:nth-3:hidden'

/**
 * Draws the figures at one step in the climb's upper corner, the return so far
 * over the step, what the step's press paid, and what each term has paid.
 */
export function drawFigures(figures: Figures) {
  return (
    <div class={FIGURES.figures}>
      <span class={LABEL}>Return so far</span>
      <span class="grid justify-items-start gap-2">
        <span class={FIGURES.total}>{figures.total}</span>
        <span class={DETAIL}>{figures.step}</span>
      </span>
      <span class={[LABEL, 'mt-2']}>This press paid</span>
      <Chip class="w-full" {...figures.paid} />
      <span class={[LABEL, 'mt-2']}>Each term so far</span>
      <span class={FIGURES.chips}>
        {figures.terms.map(chip => <Chip class={['w-full', NOTE]} key={chip.role} {...chip} />)}
      </span>
    </div>
  )
}

/**
 * The key beneath the widget, on the screen's and the climb's two columns: the
 * players' hues under the screen, and under the climb each term's hue beside
 * what one press of it pays, the two keys stacked one over the other below the
 * widget's 60rem.
 */
export const RewardKey = defineComponent({
  name  : 'RewardKey',
  setup : () => {
    const paying = keyTerms()

    return () => (
      <div class={FIGURES.key}>
        <Key entries={PLAYERS} label="The players, on every widget" />
        <Key entries={paying} label="What one press pays, on every widget" />
      </div>
    )
  }
})
