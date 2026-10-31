import WORLD      from '../art/world.json' with { type: 'json' }
import { SQUARE } from '../game/screen.ts'

/**
 * How a Glitch City lays its blocks over the screen, the blocks across and
 * down and the screen Y of the top row, which sits on the screen's grid of
 * squares as every view the game draws does.
 */
export interface City {
  columns : number
  rows    : number
  top     : number
}

/**
 * The top left of one of a room's map blocks in the room's image, in pixels.
 */
export type Origin = readonly [x: number, y: number]

/**
 * A room as far as its blocks are read from its image, its width, its height,
 * and the pad around it, in squares.
 */
export type Room = Pick<(typeof WORLD)['pallet'], 'h' | 'pad' | 'w'>

/**
 * The pixels on each side of a map block, two squares by two, the unit
 * pret/pokered's `wOverworldMap` holds a map in.
 */
const BLOCK = 2 * SQUARE

/**
 * The Glitch City every missing address draws, five blocks across and five down
 * from the screen's top left, covering its 160 pixels across and 144 down.
 */
const CITY: City = { columns: 5, rows: 5, top: 0 }

/**
 * Finds the map blocks `room`, Pallet Town unless given another, is built from
 * in `image`, the pixels of its image, each block told apart by its pixels and
 * kept once, in reading order from the top left of the map inside the pad.
 */
export function blocksOf(image: Pick<ImageData, 'data' | 'width'>, room: Room = WORLD.pallet): Origin[] {
  const pad    = room.pad * SQUARE
  const blocks = new Map<string, Origin>()
  for (let row = 0; row < room.h / 2; row++) {
    for (let column = 0; column < room.w / 2; column++) {
      const origin: Origin = [pad + column * BLOCK, pad + row * BLOCK]
      const key            = Array.from({ length: BLOCK }, (_, line) => {
        const start = ((origin[1] + line) * image.width + origin[0]) * 4
        return image.data.subarray(start, start + BLOCK * 4).join()
      }).join(';')
      if (!blocks.has(key)) blocks.set(key, origin)
    }
  }
  return [...blocks.values()]
}

/**
 * Reads the bytes of `address` as the block numbers a Glitch City lays out, one
 * to each block of `city` from the top left, cycling through the address, each
 * byte picking one of `count` blocks as the game reads bytes that are not a map
 * as block numbers past the 1,300 bytes of `wOverworldMap` (`ram/wram.asm`
 * line 191) or through a warp that leads to no warp.
 *
 * Returns:
 *   The index of the block each place of the city takes, in reading order.
 */
export function cityOf(address: string, count: number, city: City = CITY): number[] {
  const bytes = new TextEncoder().encode(address)
  return Array.from({ length: city.columns * city.rows }, (_, at) => bytes[at % bytes.length]! % count)
}

/**
 * Draws the Glitch City `address` reads as onto `context`, each of its places
 * taking the block of `blocks` its byte picks, cut from `image`, the room's
 * image those blocks were found in.
 */
export function paintCity(
  context : Pick<CanvasRenderingContext2D, 'drawImage'>,
  image   : CanvasImageSource,
  address : string,
  blocks  : readonly Origin[],
  city    : City = CITY
): void {
  for (const [at, block] of cityOf(address, blocks.length, city).entries()) {
    const [x, y] = blocks[block]!
    const left   = (at % city.columns) * BLOCK
    const top    = city.top + Math.floor(at / city.columns) * BLOCK
    context.drawImage(image, x, y, BLOCK, BLOCK, left, top, BLOCK, BLOCK)
  }
}
