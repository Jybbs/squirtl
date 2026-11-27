// @vitest-environment happy-dom
import { describe, expect, it, vi } from 'vitest'

import { RoomImages } from '../../../../../docs/.vitepress/lib/game/images.ts'
import { GameScreen } from '../../../../../docs/.vitepress/lib/game/screen.ts'
import { SEARCH }     from '../../../../../docs/.vitepress/lib/methods/search.ts'
import * as moments   from '../../../../../docs/.vitepress/lib/methods/search/moments.ts'
import { CopyScreen } from '../../../../../docs/.vitepress/lib/methods/search/screens.ts'

/**
 * The slot of the first iteration's first group holding a copy that presses
 * at least three times and then moves to its group's winner.
 */
const SLOT = SEARCH.iterations[0]!.groups[0]!.copies
  .findIndex(copy => copy.presses.length >= 3 && copy.node !== SEARCH.iterations[0]!.groups[0]!.next)

/**
 * Shows the copy at `SLOT` on a fresh screen at each moment of `at`, reading
 * after each the glides the screen has started and the fade of its last snap,
 * none before the first.
 */
function calls(at: readonly number[]): unknown[][] {
  const follow = vi.spyOn(GameScreen.prototype, 'follow')
  const snap   = vi.spyOn(GameScreen.prototype, 'snap')
  const screen = new CopyScreen(new RoomImages(() => new Image()))
  return at.map(moment => {
    screen.show(moments.shownOf(0, moment)[0]![SLOT]!)
    return [follow.mock.calls.length, snap.mock.calls.at(-1)?.[0] ?? null]
  })
}

describe('a copy’s screen', () => {
  it.each([
    {
      at   : [1, 2],
      case : 'glides through each next press from the node it began on',
      made : [[1, null], [2, null]]
    },
    {
      at   : [1, 3],
      case : 'replays without a fade where it jumps past the next press',
      made : [[1, null], [1, false]]
    },
    {
      at   : [2, 2],
      case : 'stands still where it is shown the moment it shows',
      made : [[0, false], [0, false]]
    },
    {
      at   : [1, moments.MOVED],
      case : 'fades in on its winner’s saved state once its group moves',
      made : [[1, null], [1, true]]
    }
  ])('$case', ({ at, made }) => {
    expect([SLOT >= 0, calls(at)]).toStrictEqual([true, made])
  })
})
