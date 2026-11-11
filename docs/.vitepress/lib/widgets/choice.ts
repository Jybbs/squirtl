import * as toggleGroup                               from '@zag-js/toggle-group'
import { type PropTypes, normalizeProps, useMachine } from '@zag-js/vue'
import { type ComputedRef, computed, ref, useId }     from 'vue'

/**
 * The props the group of options and each option take, as the Vue adapter
 * writes them.
 */
type Api = toggleGroup.Api<PropTypes>

/**
 * Makes `values` a group of options on Zag.js's toggle group machine with one
 * pressed at a time and none left unpressed, which renders it as a radio
 * group, holds the option pressed and its ARIA attributes, and moves focus
 * among the options with the arrow keys from one tab stop, calling `chosen`
 * with each option a reader presses other than the one already pressed.
 *
 * Returns:
 *   The props of the group, and the props of each option by its value.
 */
export function useChoice<Value extends string>(values: readonly Value[], chosen: (value: Value) => void): {
  item : (value: Value) => ReturnType<Api['getItemProps']>
  root : ComputedRef<ReturnType<Api['getRootProps']>>
} {
  const id      = useId()
  const pressed = ref<Value>(values[0]!)
  const service = useMachine(toggleGroup.machine, computed(() => ({
    deselectable  : false,
    id            : id,
    onValueChange : ({ value }: toggleGroup.ValueChangeDetails) => {
      if (value[0] === pressed.value) return
      pressed.value = value[0] as Value
      chosen(pressed.value)
    },
    value         : [pressed.value]
  })))
  const api = computed(() => toggleGroup.connect(service, normalizeProps))

  return {
    item : value => api.value.getItemProps({ value }),
    root : computed(() => api.value.getRootProps())
  }
}
