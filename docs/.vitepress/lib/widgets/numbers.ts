/**
 * The locale every figure is set in, which groups thousands with commas and
 * marks the decimal with a point.
 */
const LOCALE = 'en-US'

/**
 * The minus sign, which a figure takes in place of the hyphen the locale
 * writes.
 */
export const MINUS = '−'

/**
 * Joins a list of figures with commas and a closing "and", as a sentence lists
 * them.
 */
const andList = new Intl.ListFormat(LOCALE, { type: 'conjunction' })

/**
 * Sets `value` with its thousands grouped and at most three decimal places.
 */
export function count(value: number): string {
  return value.toLocaleString(LOCALE)
}

/**
 * Sets `value` with its thousands grouped beside the noun it counts, `one` for
 * a count of one and `many` for every other count.
 */
export function counted(value: number, one: string, many = `${one}s`): string {
  return `${count(value)} ${value === 1 ? one : many}`
}

/**
 * Sets `value` to exactly `places` decimal places, a negative figure taking the
 * minus sign and, where `sign` is `exceptZero`, a positive one the plus sign.
 */
export function fixed(value: number, places: number, sign: 'auto' | 'exceptZero' = 'auto'): string {
  const digits = { maximumFractionDigits: places, minimumFractionDigits: places, signDisplay: sign }
  return value.toLocaleString(LOCALE, digits).replace('-', MINUS)
}

/**
 * Sets each of `values` with its thousands grouped and joins them with commas
 * and a closing "and", as a sentence lists them.
 */
export function listed(values: readonly number[]): string {
  return andList.format(values.map(value => count(value)))
}

/**
 * Sets `value` to `places` decimal places behind a plus sign where it is
 * positive and a minus sign where it is negative, a figure that rounds to zero
 * taking neither.
 */
export function signed(value: number, places: number): string {
  return fixed(value, places, 'exceptZero')
}

/**
 * Names the step `at` out of an episode's `last` steps.
 */
export function stepText(at: number, last: number): string {
  return `Step ${count(at)} of ${count(last)}`
}
