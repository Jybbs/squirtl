import { describe, expect, it } from 'vitest'

import { runsOf }          from '../../../lib/drawing/sprites.ts'
import * as actors         from '../../../lib/game/actors.ts'
import { Episode }         from '../../../lib/game/episode.ts'
import type { Square }     from '../../../lib/game/rooms.ts'
import { IDENTITY, hexOf } from '../../../lib/identity/identity.ts'
import { stand }           from '../../common/episode.ts'

describe('frameFor', () => {
  it.each([
    ['player', 'down', false, 0, false],
    ['player', 'up', false, 1, false],
    ['player', 'left', false, 2, false],
    ['player', 'right', false, 2, true],
    ['player', 'down', true, 3, false],
    ['player', 'up', true, 4, false],
    ['oak', 'right', true, 5, true],
    ['mom', 'left', true, 2, false],
    ['mom', 'up', true, 1, false],
    ['ball', 'left', false, 0, false]
  ] as const)('shows %s facing %s walking %s as frame %i', (name, facing, walking, frame, mirrored) => {
    const grid = IDENTITY.sprites[name].frames[frame]

    expect(actors.frameFor(name, facing, walking)).toStrictEqual({ grid, mirrored })
  })

  it('reads one pose each time it is asked for it', () => {
    expect(actors.frameFor('rival', 'up', true)).toBe(actors.frameFor('rival', 'up', true))
  })
})

describe('actorsOf', () => {
  it('stands Mom in the house on 5, 4 facing left, and nobody in the bedroom', () => {
    expect([actors.actorsOf(stand([3, 3], 'house')), actors.actorsOf(new Episode())])
      .toStrictEqual([[{ at: [5, 4], facing: 'left', name: 'mom', stepping: false }], []])
  })

  it('stands Oak at his table, the rival beside it, and the Poké Balls on it in the lab', () => {
    const names = actors.actorsOf(stand([5, 6], 'lab')).map(actor => [actor.name, actor.at])

    expect(names).toStrictEqual([
      ['oak', [5, 2]], ['rival', [4, 3]], ['ball', [6, 3]], ['ball', [7, 3]], ['ball', [8, 3]]
    ])
  })

  it('takes the chosen Poké Ball off the table', () => {
    const game  = stand([7, 4], 'lab')
    game.chosen = [7, 3]

    const balls = actors.actorsOf(game).filter(actor => actor.name === 'ball')

    expect(balls.map(actor => actor.at)).toStrictEqual([[6, 3], [8, 3]])
  })

  it('stands Oak where he leads Blue in place of his table, or where a glide sets him', () => {
    const game  = stand([5, 9], 'lab')
    game.leader = { at: [5, 8], facing: 'up', place: 'lab' }
    const oaks  = (leaderAt?: Square, stepping?: boolean) => actors.actorsOf(game, leaderAt, stepping)
      .filter(actor => actor.name === 'oak')

    expect(oaks()).toStrictEqual([{ at: [5, 8], facing: 'up', name: 'oak', stepping: false }])
    expect(oaks([5, 8.5], true)).toStrictEqual([{ at: [5, 8.5], facing: 'up', name: 'oak', stepping: true }])
  })

  it('leaves Oak out of a room he leads Blue in from another', () => {
    const game  = stand([12, 12], 'pallet')
    game.leader = { at: [5, 10], facing: 'up', place: 'lab' }

    expect(actors.actorsOf(game)).toStrictEqual([])
  })
})

describe('spriteMark and termMark', () => {
  it('draws a sprite’s first frame as a square mark in the Game Boy’s shades, one rectangle a run', () => {
    const mark = actors.spriteMark('ball')

    expect(mark).toMatch(/^<svg viewBox="0 0 16 16" shape-rendering="crispEdges">/u)
    expect(mark.match(/<rect /gu)).toHaveLength(runsOf(IDENTITY.sprites.ball.frames[0]!).length)
    expect(mark).toContain(`fill="${hexOf('night')}"`)
  })

  it('draws a sprite’s mark in the fills given', () => {
    const fills = ['#000001', '#000002', '#000003', '#000004']
    const mark  = actors.spriteMark('player', fills)

    expect(mark).toMatch(/^<svg viewBox="0 0 16 16"/u)
    expect(mark.match(/#[\da-f]{6}/gu)).toDrawFrom(fills)
    expect(mark).toContain(fills[2])
  })

  it.each([
    ['milestone', actors.spriteMark('oak')],
    ['starter', actors.spriteMark('ball')],
    ['novelty', '<svg viewBox="0 0 12 12"><circle cx="6" cy="6" r="3" fill="currentColor"/></svg>']
  ] as const)('marks the term %s as the game does on the board', (term, mark) => {
    expect(actors.termMark(term)).toBe(mark)
  })
})
