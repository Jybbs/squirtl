import { Episode }                       from '../../lib/game/episode.ts'
import type { Direction, Place, Square } from '../../lib/game/rooms.ts'

/**
 * Stands Blue on `at` in `place` of `game`, a fresh episode unless one is given,
 * stopped facing `facing` where it is given.
 */
export function stand(at: Square, place: Place, facing?: Direction, game: Episode = new Episode()): Episode {
  game.place = place
  game.at    = at
  if (facing) {
    game.facing   = facing
    game.lastStop = facing
  }
  return game
}
