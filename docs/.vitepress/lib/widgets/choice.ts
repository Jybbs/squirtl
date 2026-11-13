import * as toggleGroup                                     from '@zag-js/toggle-group'
import { type PropTypes, normalizeProps, useMachine }       from '@zag-js/vue'
import { type ComputedRef, type Ref, computed, ref, useId } from 'vue'

/**
 * The props the group of options and each option take, as the Vue adapter
 * writes them.
 */
type Api = toggleGroup.Api<PropTypes>

/**
 * A group of options, the props of the group and the props of each option by
 * its value.
 */
export interface Options<Value extends string> {
  item : (value: Value) => ReturnType<Api['getItemProps']>
  root : ComputedRef<ReturnType<Api['getRootProps']>>
}

/**
 * Runs Zag.js's toggle group machine on the context `context` reads, under an
 * id of its own.
 */
function optionsOf<Value extends string>(context: () => Omit<toggleGroup.Props, 'id'>): Options<Value> {
  const id      = useId()
  const service = useMachine(toggleGroup.machine, computed(() => ({ id, ...context() })))
  const api     = computed(() => toggleGroup.connect(service, normalizeProps))

  return {
    item : value => api.value.getItemProps({ value }),
    root : computed(() => api.value.getRootProps())
  }
}

/**
 * Makes `values` a group of options on Zag.js's toggle group machine with one
 * pressed at a time and none left unpressed, which renders it as a radio
 * group, holds the option pressed and its ARIA attributes, and moves focus
 * among the options with the arrow keys from one tab stop, calling `chosen`
 * with each option a reader presses other than the one already pressed. The
 * option pressed is held in `pressed`, the first option unless the caller
 * hands a ref of its own, which it may set itself.
 *
 * Returns:
 *   The props of the group, and the props of each option by its value.
 */
export function useChoice<Value extends string>(values: readonly Value[], chosen: (value: Value) => void, pressed: Ref<Value> = ref(values[0]!) as Ref<Value>): Options<Value> {
  return optionsOf(() => ({
    deselectable  : false,
    onValueChange : ({ value }: toggleGroup.ValueChangeDetails) => {
      if (value[0] === pressed.value) return
      pressed.value = value[0] as Value
      chosen(pressed.value)
    },
    value         : [pressed.value]
  }))
}

/**
 * Makes `values` a group of options on Zag.js's toggle group machine with at
 * most one pressed, held in `picked`, which a press on the pressed option
 * clears and which the caller may set or clear itself, and moves focus among
 * the options with the arrow keys from one tab stop.
 *
 * Returns:
 *   The props of the group, and the props of each option by its value.
 */
export function usePick<Value extends string>(values: readonly Value[], picked: Ref<Value | null>): Options<Value> {
  return optionsOf(() => ({
    deselectable  : true,
    onValueChange : ({ value }: toggleGroup.ValueChangeDetails) => {
      picked.value = values.find(each => each === value[0]) ?? null
    },
    value         : picked.value === null ? [] : [picked.value]
  }))
}

/**
 * Makes `values` a group of toggles on Zag.js's toggle group machine, any
 * number pressed at once and held in `pressed`, which carries their ARIA
 * attributes and the keys moving focus among them from one tab stop.
 *
 * Returns:
 *   The props of the group, and the props of each toggle by its value.
 */
export function useSwitches<Value extends string>(values: readonly Value[], pressed: Ref<ReadonlySet<Value>>): Options<Value> {
  return optionsOf(() => ({
    multiple      : true,
    onValueChange : ({ value }: toggleGroup.ValueChangeDetails) => {
      pressed.value = new Set(values.filter(each => value.includes(each)))
    },
    value         : [...pressed.value]
  }))
}
