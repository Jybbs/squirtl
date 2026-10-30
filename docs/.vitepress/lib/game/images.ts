import WORLD          from '../art/world.json' with { type: 'json' }
import type { Place } from './rooms.ts'

/**
 * Loads the image at `source`, an address or a `data:` URI.
 */
export type Loader = (source: string) => HTMLImageElement

/**
 * The images of every room in the light scheme every screen draws, each loaded
 * through `load` the first time it is read and kept for every later read.
 */
export class RoomImages {
  readonly #images = new Map<Place, HTMLImageElement>()
  readonly #load   : Loader

  constructor(load: Loader = source => Object.assign(new Image(), { src: source })) {
    this.#load = load
  }

  /**
   * Reads the image of `place`, loading it on its first read.
   */
  image(place: Place): HTMLImageElement {
    const kept = this.#images.get(place)
    if (kept) return kept
    const image = this.#load(WORLD[place].image.light)
    this.#images.set(place, image)
    return image
  }

  /**
   * Loads and decodes the image of each room of `places`, every room's unless
   * given others, and calls `then` once all of them can draw, leaving it
   * uncalled where one fails to decode, a broken image `drawImage` throws on.
   */
  whenReady(then: () => void, places: readonly Place[] = Object.keys(WORLD) as Place[]): void {
    void Promise.all(places.map(place => this.image(place).decode())).then(then, () => {})
  }
}
