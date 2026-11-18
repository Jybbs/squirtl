import type { Figures } from '../../../../lib/methods/search/moments.ts'
import { count }        from '../../../../lib/widgets/numbers.ts'
import { Chip }         from '../../kit/chip.tsx'

/**
 * Draws the chips over the copies: the iteration, or the demonstration's
 * length, the tree's nodes and saved states, and the presses spent.
 */
export function drawFigures(figures: Figures) {
  return (
    <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
      <Chip
        class="w-full"
        name={figures.demonstration ? 'Demonstration' : 'Iteration'}
        value={figures.iteration}
      />
      <Chip class="w-full" name="Nodes" value={count(figures.nodes)} />
      <Chip class="w-full" name="Saved states" value={count(figures.saved)} />
      <Chip class="w-full" name="Presses spent" value={count(figures.spent)} />
    </div>
  )
}
