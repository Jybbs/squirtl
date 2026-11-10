import { describe, expect, it } from 'vitest'

import { finalsWidth } from '../../../lib/results/lanes.ts'
import { lanesOf }     from '../../../lib/results/layout.ts'
import * as results    from '../../../lib/results/results.ts'
import FIXTURE         from './fixtures/results.json' with { type: 'json' }

/**
 * The groups of the seven runs the fixture holds.
 */
const GROUPS = results.groupsOf(FIXTURE as unknown as results.Results)

/**
 * Lays the figure out `width` pixels wide with the side `side` widened.
 */
const at = (width: number, side: 'curves' | 'finals' | null) => lanesOf(GROUPS, width, finalsWidth(width, side))

/**
 * Reads the text of each label along an axis, its titles last.
 */
const axis = (drawn: { labels: readonly { text: string }[], titles: readonly { text: string }[] }) =>
  [...drawn.labels, ...drawn.titles].map(label => label.text)

/**
 * Reads where the first verdict of a stacked figure `width` pixels wide starts.
 */
const facts = (width: number) => lanesOf(GROUPS, width, 0).lanes[0]!.odds[0]!.label.x

describe('lanesOf', () => {
  it('lays out a lane a group, its heads naming the agent, the start, and the share, at rest neither side folded', () => {
    const drawn = at(688, null)

    expect(drawn.lanes.map(lane => lane.heads.map(head => head.text))).toStrictEqual([
      ['DQN · BEDROOM', '0%'],
      ['PPO · BEDROOM', '100% [90, 100]'],
      ['PPO · CURRICULUM', '100% [100, 100]'],
      ['PQN · BEDROOM', '40%'],
      ['PQN · CURRICULUM', '80%']
    ])
    expect([drawn.opened, drawn.folded, drawn.sides]).toStrictEqual([0, { curves: 0, finals: 0 }, { curves: [150, 432], finals: [432, 688] }])
  })

  it('reads each lane’s verdicts against random presses and, along the curriculum, against the bedroom', () => {
    expect(at(688, 'finals').lanes.map(lane => lane.odds.map(line => `${line.label.text} ${line.word.text}`))).toStrictEqual([
      ['VS RANDOM BELOW'],
      ['VS RANDOM BEATS'],
      ['VS RANDOM BEATS', 'VS BEDROOM NOT CLEAR'],
      ['VS RANDOM NOT CLEAR'],
      ['VS RANDOM NOT CLEAR', 'VS BEDROOM WORSE']
    ])
  })

})

describe('lanesOf’s fold', () => {
  it('opens the verdicts and folds the curves to their tab once the last evaluation widens', () => {
    const drawn = at(688, 'finals')

    expect([drawn.opened, drawn.folded]).toStrictEqual([1, { curves: 1, finals: 0 }])
  })

  it('folds the last evaluation to a tab reading its verdict against random presses once the curves widen', () => {
    const drawn = at(688, 'curves')

    expect([drawn.opened, drawn.folded, drawn.lanes.map(lane => lane.tab.word.text)]).toStrictEqual([
      0, { curves: 0, finals: 1 }, ['BELOW', 'BEATS', 'BEATS', 'NOT CLEAR', 'NOT CLEAR']
    ])
  })

})

describe('lanesOf’s lanes', () => {
  it('shades each seed’s cells by its share at each evaluation, hatching only the curriculum’s rows', () => {
    const drawn = at(688, null)

    expect(drawn.lanes.map(lane => lane.rows.map(row => [row.cells.map(cell => cell.shade), row.hatch !== null]))).toStrictEqual([
      [[[0, 0, 0], false]],
      [[[2, 3, 3], false], [[1, 3, 3], false]],
      [[[3, 3, 3], true], [[3, 3, 3], true]],
      [[[0, 1, 2], false]],
      [[[1, 2, 3], true]]
    ])
  })

  it('rises each seed from its random share to its last along the last evaluation’s track', () => {
    const drawn = at(688, 'finals')
    const [x0]  = drawn.sides!.finals

    expect(drawn.lanes[1]!.bells.map(bell => [bell.from > x0, bell.from < bell.to, bell.to < 688])).toStrictEqual([
      [true, true, true], [true, true, true]
    ])
  })

})

describe('lanesOf’s axes', () => {
  it('titles both axes with the variable and its unit', () => {
    const drawn = at(688, null)

    expect([axis(drawn.steps), axis(drawn.shares)]).toStrictEqual([
      ['0', '0.5', '1', '1.5', 'Environment steps (millions)'],
      ['0%', '25%', '50%', '75%', '100%', 'Last evaluation (% reaching it)']
    ])
  })

  it('stacks the curves above the last evaluation below its widest width, with nothing to fold', () => {
    const drawn = lanesOf(GROUPS, 390, 0)

    expect([drawn.sides, drawn.opened, drawn.folded, drawn.lanes.map(lane => lane.glyphs.length)]).toStrictEqual([
      null, 1, { curves: 0, finals: 0 }, [2, 2, 2, 2, 2]
    ])
  })

  it('sets the verdicts beside the last evaluation where a stacked figure has the room, and above it where it has not', () => {
    expect([facts(500) > 250, facts(390)]).toStrictEqual([true, 20])
  })

  it('thins the labels and breaks each title onto two lines at its narrowest', () => {
    const drawn = lanesOf(GROUPS, 220, 0)

    expect([axis(drawn.steps), axis(drawn.shares)]).toStrictEqual([
      ['0', '1.5', 'Environment steps', '(millions)'],
      ['0%', '50%', '100%', 'Last evaluation', '(% reaching it)']
    ])
  })
})
