import { describe, expect, it } from 'vitest'

import * as numbers from '../../../lib/widgets/numbers.ts'

const { MINUS } = numbers

describe('fixed', () => {
  it.each([
    [0.5, 2, '0.50'],
    [-0.25, 3, `${MINUS}0.250`],
    [1234.5, 1, '1,234.5'],
    [0.000123, 5, '0.00012']
  ])('sets %f to %i places as %s', (value, places, text) => {
    expect(numbers.fixed(value, places)).toBe(text)
  })
})

describe('signed', () => {
  it.each([
    [0.1, 5, '+0.10000'],
    [-0.00025, 5, `${MINUS}0.00025`],
    [0, 2, '0.00']
  ])('signs %f to %i places as %s', (value, places, text) => {
    expect(numbers.signed(value, places)).toBe(text)
  })
})

describe('count', () => {
  it.each([
    [10240, '10,240'],
    [0.12345, '0.123']
  ])('sets %f as %s', (value, text) => {
    expect(numbers.count(value)).toBe(text)
  })
})

describe('listed', () => {
  it.each([
    [[6], '6'],
    [[40, 50], '40 and 50'],
    [[6, 30, 1234], '6, 30, and 1,234']
  ])('lists %j as %s', (values, text) => {
    expect(numbers.listed(values)).toBe(text)
  })
})

describe('stepText', () => {
  it.each([
    [0, 163, 'Step 0 of 163'],
    [1234, 10240, 'Step 1,234 of 10,240']
  ])('names step %i of %i as %s', (at, last, text) => {
    expect(numbers.stepText(at, last)).toBe(text)
  })
})
