import * as sprites     from '../../drawing/sprites.ts'
import { EMOTES }       from '../../front/learning/walker.ts'
import { spriteMark }   from '../../game/actors.ts'
import { spriteShades } from '../../identity/identity.ts'

/**
 * The key's entries, Blue walking, Oak calling him back, and the pad.
 */
export const KEY = [
  { mark: spriteMark('player'), name: 'Blue', note: 'Blue walking the walk up to the north edge once a pass', role: 'none' },
  {
    mark : `<svg viewBox="0 0 16 16" shape-rendering="crispEdges">${sprites.spriteMarkup(EMOTES.shock, { fills: spriteShades, size: 1, x: 0, y: 0 })}</svg>`,
    name : 'Oak calls him back',
    note : 'Where the walk pays, Oak calling Blue back at the north edge under the shock bubble',
    role : 'milestone'
  },
  {
    mark : '<svg viewBox="0 0 16 16" shape-rendering="crispEdges"><path d="M6 1h4v5h5v4h-5v5h-4v-5h-5v-4h5z" fill="none" stroke="currentColor" stroke-width="1" opacity=".55"/><rect x="6.5" y="2" width="3" height="4" fill="currentColor"/></svg>',
    name : 'Each press',
    note : 'The Game Boy’s pad on a square, each arm filled as far as its learner’s value or odds of that press reach',
    role : 'agent'
  }
] as const
