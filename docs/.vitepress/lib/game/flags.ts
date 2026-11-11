import EVENTS         from '../rendered/events.json' with { type: 'json' }
import type { Term } from './episode.ts'

/**
 * One event flag the network reads, the flag the model of the game sets for
 * it, its name on a widget, and the term of the reward the step first setting
 * it pays.
 */
export interface EventFlag {
  flag : Flag
  name : string
  term : Term
}

/**
 * A moment in the game an event flag marks, each milestone's and the starter's.
 */
export type Flag = (typeof FLAGS)[keyof typeof FLAGS]['flag']

/**
 * The flag the model of the game sets for each event flag the network reads,
 * beside the name a widget gives it, under the name the package's `Event`
 * gives the flag.
 */
const FLAGS = {
  EVENT_FOLLOWED_OAK_INTO_LAB   : { flag: 'followed', name: 'Followed Oak' },
  EVENT_GOT_STARTER             : { flag: 'starter', name: 'Got the starter' },
  EVENT_OAK_APPEARED_IN_PALLET  : { flag: 'appeared', name: 'Oak appeared' },
  EVENT_OAK_ASKED_TO_CHOOSE_MON : { flag: 'asked', name: 'Oak asked' }
} as const

/**
 * The event flags the network reads, in the order the package's `Event`
 * declares them, each beside the term of the reward the step first setting it
 * pays.
 */
export const eventFlags: readonly EventFlag[] = EVENTS.map(event =>
  Object.assign({ term: event.term as Term }, FLAGS[event.name as keyof typeof FLAGS]))

/**
 * The flags of the milestones on the way to the starter, those whose events pay
 * a milestone.
 */
export const milestones: readonly Flag[] = eventFlags
  .filter(each => each.term === 'milestone')
  .map(each => each.flag)
