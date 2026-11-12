import { type Ref, ref } from 'vue'

import { type Options, useSwitches } from '../widgets/choice.ts'
import type { Group }  from './results.ts'

/**
 * Reads how far the curves of `group`'s agent part, as how far the probability
 * that a run along the curriculum beats a run from the bedroom stands from even
 * odds, zero for a group from the bedroom.
 */
const parting = (group: Group): number => Math.abs((group.comparison.bedroom?.value ?? 0.5) - 0.5)

/**
 * Picks the groups pressed before a reader presses any, the runs from the
 * bedroom and along the curriculum of the agent whose curves part furthest,
 * the first group's agent where none parts.
 */
function pressedOf(groups: readonly Group[]): string[] {
  const [furthest] = groups.toSorted((left, right) => parting(right) - parting(left))
  return groups.filter(group => group.agent === furthest!.agent).map(group => group.id)
}

/**
 * Makes the groups a group of toggles, any number pressed at once and those
 * `pressedOf` picks pressed first.
 *
 * Returns:
 *   The keys of the groups pressed, the props of the group of toggles, and the
 *   props of each toggle by its group's key.
 */
export function useToggles(groups: readonly Group[]): Options<string> & { pressed: Ref<ReadonlySet<string>> } {
  const keys    = groups.map(group => group.id)
  const pressed = ref<ReadonlySet<string>>(new Set(pressedOf(groups)))

  return { ...useSwitches(keys, pressed), pressed }
}
