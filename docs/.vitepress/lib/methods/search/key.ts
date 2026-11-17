import { termMark }      from '../../game/actors.ts'
import type { KeyEntry } from '../../widgets/chips.ts'
import type { Shown }    from './moments.ts'

/**
 * The marks the copies carry, in the order the key lists them: the ring round
 * each group's winner, the cross over a dead copy, and the badge a copy
 * carries once its rollout sets a milestone's flag.
 */
const MARKED = ['win', 'dead', 'milestone'] as const

/**
 * The cross drawn over a dead copy's screen.
 */
export const CROSS = '<svg viewBox="0 0 16 16"><path d="M4 4l8 8M12 4l-8 8" fill="none" '
                   + 'stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>'
/**
 * The mark of a milestone, which the reward chips carry.
 */
export const MILESTONE = termMark('milestone')
/**
 * The widget's key, each entry the mark the copies carry.
 */
export const KEY: readonly KeyEntry[] = [
  {
    mark : '<svg viewBox="0 0 16 16"><rect x="2" y="3" width="12" height="10" fill="none" '
         + 'stroke="currentColor" stroke-width="2.5"/></svg>',
    name : 'The winner',
    note : 'The group’s winner, the copy whose lineage the reward pays most and then the one with the '
         + 'highest uncertainty'
  },
  {
    mark : CROSS,
    name : 'A dead copy',
    note : 'Back on the screen and the square it began on, dimmed and crossed out'
  },
  {
    mark : MILESTONE,
    name : 'A milestone',
    note : 'A milestone’s flag set in the rollout, which ends it',
    role : 'milestone'
  }
]

/**
 * Reports whether `shown` carries the mark entry `n` of the key names.
 */
export function carries(shown: Shown, n: number): boolean {
  const marked = MARKED[n]
  return marked === 'milestone' ? shown.term !== null : shown.state === marked
}
