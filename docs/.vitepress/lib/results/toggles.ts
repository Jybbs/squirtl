import { type Ref, ref } from 'vue'

import { type Options, useSwitches } from '../widgets/choice.ts'
import type { Group }  from './results.ts'

/**
 * The groups pressed before a reader presses any, PQN's runs from the bedroom
 * and along the curriculum, whose curves part furthest.
 */
const PRESSED = ['pqn-bedroom', 'pqn-curriculum']

/**
 * Makes the groups a group of toggles, any number pressed at once, the groups
 * `PRESSED` names pressed first where `groups` holds them and the first group
 * otherwise.
 *
 * Returns:
 *   The keys of the groups pressed, the props of the group of toggles, and the
 *   props of each toggle by its group's key.
 */
export function useToggles(groups: readonly Group[]): Options<string> & { pressed: Ref<ReadonlySet<string>> } {
  const keys    = groups.map(group => group.id)
  const first   = PRESSED.filter(key => keys.includes(key))
  const pressed = ref<ReadonlySet<string>>(new Set(first.length > 0 ? first : keys.slice(0, 1)))

  return { ...useSwitches(keys, pressed), pressed }
}
