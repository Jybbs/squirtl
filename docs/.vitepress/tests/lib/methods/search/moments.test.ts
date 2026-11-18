import { describe, expect, it } from 'vitest'

import { LAST, SEARCH, SIZES } from '../../../../lib/methods/search.ts'
import * as moments            from '../../../../lib/methods/search/moments.ts'

/**
 * The search's first iteration.
 */
const FIRST = SEARCH.iterations[0]!
/**
 * The first copy whose rollout sets a flag, beside its iteration, its group,
 * and its slot.
 */
const FLAGGED = SEARCH.iterations.flatMap(({ groups }, at) => groups.flatMap((group, g) =>
  group.copies.map((copy, slot) => ({ at, copy, g, slot }))))
  .find(({ copy }) => copy.term !== null)!
/**
 * The mark each copy of the first group of the first iteration carries once
 * its rollout ends.
 */
const MARKS = FIRST.groups[0]!.copies.map((copy, slot) => {
  if (slot === FIRST.groups[0]!.winner) return 'win'
  return copy.dead ? 'dead' : 'lost'
})

/**
 * Reads the copies of the first iteration once they have moved, those moved
 * beside those left standing.
 */
function movedOf(shown: readonly moments.Shown[]): [moments.Shown[], moments.Shown[]] {
  return [shown.filter(each => each.state === 'moved'), shown.filter(each => each.state !== 'moved')]
}

describe('the moments', () => {
  it.each([
    { moment: 1, t: 0 },
    { moment: 1, t: moments.TIMING.press - 1 },
    { moment: 2, t: moments.TIMING.press },
    { moment: SIZES.presses, t: moments.ROLLING - 1 },
    { moment: moments.ENDED, t: moments.ROLLING },
    { moment: moments.ENDED, t: moments.ROLLING + moments.TIMING.move - 1 },
    { moment: moments.MOVED, t: moments.ROLLING + moments.TIMING.move }
  ])('stands at moment $moment $t milliseconds into an iteration', ({ moment, t }) => {
    expect(moments.momentOf(t)).toBe(moment)
  })

  it('shows each copy’s first press, no mark, and no uncertainty while its rollout plays', () => {
    const [group] = moments.shownOf(0, 1)

    expect(group!.map(each => [each.pressed, each.state, each.uncertainty]))
      .toStrictEqual(group!.map(() => [1, '', null]))
  })

  it('marks each copy and shows its uncertainty once its rollout ends', () => {
    const ended = moments.shownOf(0, moments.ENDED)[0]!

    expect([ended.map(each => each.state), ended.map(each => each.uncertainty)])
      .toStrictEqual([MARKS, FIRST.groups[0]!.copies.map(copy => copy.uncertainty)])
  })

  it('moves every copy off its group’s next node there, carrying that node’s total', () => {
    const [moved, standing] = movedOf(moments.shownOf(0, moments.MOVED).flat())

    expect(moved.map(each => [each.pressed, each.total]))
      .toStrictEqual(moved.map(each => [0, SEARCH.nodes[each.from]!.total]))
    expect(standing.map(each => each.copy.node)).toStrictEqual(FIRST.groups.map(group => group.next))
  })

  it('shows the demonstration as the last iteration ended, ringing only the copy choosing a starter', () => {
    const last = moments.shownOf(LAST, 0).flat()

    expect(last.filter(each => each.state === 'win').map(each => each.term)).toStrictEqual(['goal'])
    expect(last.filter(each => each.state !== 'win').map(each => each.state))
      .toStrictEqual(last.slice(1).map(() => ''))
    expect(last.map(each => each.pressed)).toStrictEqual(last.map(each => each.copy.presses.length))
  })
})

describe('a rollout setting a flag', () => {
  it('shows a flag’s term only at the press setting it, its copy standing there after', () => {
    const { at, copy, g, slot } = FLAGGED
    const shown                 = [copy.presses.length - 1, copy.presses.length, SIZES.presses]
      .map(moment => moments.shownOf(at, moment)[g]![slot]!)

    expect(shown.map(each => [each.pressed, each.term])).toStrictEqual([
      [copy.presses.length - 1, null], [copy.presses.length, copy.term], [copy.presses.length, copy.term]
    ])
  })
})

describe('the words', () => {
  it('names an iteration, or the demonstration and its length', () => {
    expect([moments.describe(0), moments.describe(LAST)]).toStrictEqual([
      `Iteration 1 of ${LAST}`, `The demonstration, ${SEARCH.demonstration.length} presses`
    ])
  })

  it('counts nothing before the first rollouts end, and the last iteration’s figures at the end', () => {
    const last = SEARCH.iterations.at(-1)!

    expect(moments.figuresOf(0, 1))
      .toStrictEqual({ demonstration: false, iteration: `1 of ${LAST}`, nodes: 1, saved: 1, spent: 0 })
    expect(moments.figuresOf(LAST, 0)).toStrictEqual({
      demonstration : true,
      iteration     : `${SEARCH.demonstration.length} presses`,
      nodes         : last.nodes,
      saved         : last.saved,
      spent         : last.spent
    })
  })

  it('counts the first iteration once its rollouts end', () => {
    const { nodes, saved, spent } = FIRST

    expect(moments.figuresOf(0, moments.ENDED)).toMatchObject({ nodes, saved, spent })
  })
})
