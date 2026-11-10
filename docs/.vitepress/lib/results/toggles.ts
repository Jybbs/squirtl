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
 * The groups pressed before a reader presses any, PQN's runs from the bedroom
 * and along the curriculum, whose curves part furthest.
 */
const PRESSED = ['pqn-bedroom', 'pqn-curriculum']

/**
 * Makes the groups a group of toggles on Zag.js's toggle group machine, any
 * number pressed at once, which holds their pressed states, their ARIA
 * attributes, and the keys moving focus among them with one tab stop.
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
  const keys    = groups.map(group => group.id)
  const first   = PRESSED.filter(key => keys.includes(key))
  const pressed = ref<ReadonlySet<string>>(new Set(first.length > 0 ? first : keys.slice(0, 1)))
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
