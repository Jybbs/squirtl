import * as toggleGroup                                     from '@zag-js/toggle-group'
import { type PropTypes, normalizeProps, useMachine }       from '@zag-js/vue'
import { type ComputedRef, type Ref, computed, ref, useId } from 'vue'

import type { Group } from './results.ts'

/**
 * The props the group of toggles and each toggle take, as the Vue adapter
 * writes them.
 */
type Api = toggleGroup.Api<PropTypes>

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
 * Makes the groups a group of toggles on Zag.js's toggle group machine, any
 * number pressed at once and those `pressedOf` picks pressed first, which holds
 * their pressed states, their ARIA attributes, and the keys moving focus among
 * them with one tab stop.
 *
 * Returns:
 *   The keys of the groups pressed, the props of the group of toggles, and the
 *   props of each toggle by its group's key.
 */
export function useToggles(groups: readonly Group[]): {
  item    : (key: string) => ReturnType<Api['getItemProps']>
  pressed : Ref<ReadonlySet<string>>
  root    : ComputedRef<ReturnType<Api['getRootProps']>>
} {
  const id      = useId()
  const pressed = ref<ReadonlySet<string>>(new Set(pressedOf(groups)))
  const service = useMachine(toggleGroup.machine, computed(() => ({
    id            : id,
    multiple      : true,
    onValueChange : ({ value }: toggleGroup.ValueChangeDetails) => { pressed.value = new Set(value) },
    value         : [...pressed.value]
  })))
  const api = computed(() => toggleGroup.connect(service, normalizeProps))

  return {
    item    : key => api.value.getItemProps({ value: key }),
    pressed : pressed,
    root    : computed(() => api.value.getRootProps())
  }
}
