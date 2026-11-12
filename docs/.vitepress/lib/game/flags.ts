import EVENTS         from '../rendered/events.json' with { type: 'json' }
import type { Term } from './episode.ts'

/**
 * One event flag the network reads, the flag the model of the game sets for
 * it, its index in `wEventFlags`, its name on a widget, and the term of the
 * reward the step first setting it pays toward the default goal.
 */
export interface EventFlag {
  flag  : Flag
  index : number
  name  : string
  term  : Term
}

/**
 * A moment in the game an event flag marks that the model sets, from Oak appearing to the starter.
 */
export type Flag = (typeof FLAGS)[keyof typeof FLAGS]['flag']

/**
 * The flag the model of the game names for each event flag it sets, beside the
 * name a widget gives it, under the name the package's `Event` gives the flag.
 */
const FLAGS = {
  EVENT_FOLLOWED_OAK_INTO_LAB   : { flag: 'followed', name: 'Followed Oak' },
  EVENT_GOT_STARTER             : { flag: 'starter', name: 'Got the starter' },
  EVENT_OAK_APPEARED_IN_PALLET  : { flag: 'appeared', name: 'Oak appeared' },
  EVENT_OAK_ASKED_TO_CHOOSE_MON : { flag: 'asked', name: 'Oak asked' }
} as const

/**
 * The event flags the model of the game sets, those up to the default goal, in
 * the order the package's `Event` declares them, each beside the term of the
 * reward the step first setting it pays.
 */
export const eventFlags: readonly EventFlag[] = EVENTS.flatMap(({ index, name, term }) =>
  term ? [Object.assign({ index, term: term as Term }, FLAGS[name as keyof typeof FLAGS])] : [])

/**
 * The flags of the milestones on the way to the starter, those whose events pay
 * a milestone.
 */
export const milestones: readonly Flag[] = eventFlags
  .filter(each => each.term === 'milestone')
  .map(each => each.flag)
