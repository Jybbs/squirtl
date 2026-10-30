import type { DOMWrapper, VueWrapper } from '@vue/test-utils'
import { vi }                          from 'vitest'

/**
 * An element a case moves a pointer across, the events it takes beside the box
 * a pointer's position along it is read against.
 */
type Control = Pick<DOMWrapper<Element>, 'element' | 'trigger'>

/**
 * Reads the control of the slider a widget in `wrapper` makes of its drawing,
 * the part Zag.js marks `control`, laid out `width` pixels wide from the
 * viewport's left edge.
 */
export function controlOf(wrapper: VueWrapper, width: number): Control {
  return laidOut(wrapper.get("[data-part='control']"), width)
}

/**
 * Lays `control` out `width` pixels wide from `left` pixels in from the
 * viewport's left edge, and returns it.
 */
export function laidOut<C extends Control>(control: C, width: number, left = 0): C {
  vi.spyOn(control.element, 'getBoundingClientRect').mockReturnValue({ left, width } as DOMRect)
  return control
}

/**
 * Presses a mouse's main button on `control` at `clientX` pixels from the
 * viewport's left edge.
 */
export async function press(control: Pick<Control, 'trigger'>, clientX: number): Promise<void> {
  await control.trigger('pointerdown', { button: 0, clientX, clientY: 0, pointerType: 'mouse' })
}

/**
 * Reads the value a widget's slider stands at beside the text it gives a screen
 * reader.
 */
export function sliderState(wrapper: VueWrapper): [string | undefined, string | undefined] {
  const thumb = wrapper.get('[role="slider"]')
  return [thumb.attributes('aria-valuenow'), thumb.attributes('aria-valuetext')]
}

/**
 * Moves a mouse across `control` through each of `points` along it, after
 * entering it.
 */
export async function sweep(control: Pick<Control, 'trigger'>, points: readonly number[]): Promise<void> {
  await control.trigger('pointerenter', { pointerType: 'mouse' })
  await Promise.all(points.map(clientX => control.trigger('pointermove', { clientX, pointerType: 'mouse' })))
}
