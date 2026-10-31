import { spriteShades } from '../identity/identity.ts'

/**
 * The background palette with every color of a room keeping its own shade,
 * written as the Game Boy's `rBGP` lists the shades of colors 3 to 0.
 */
export const PLAIN = '3210'

/**
 * Reads how light the color `packed` holds is, the sum of its red, green, and
 * blue bytes.
 */
function lightness(packed: number): number {
  return (packed >> 16) + ((packed >> 8) & 255) + (packed & 255)
}

/**
 * Reads the red, green, and blue bytes of the pixel at byte `at` of `pixels` as
 * one number.
 */
function packedAt(pixels: Uint8ClampedArray, at: number): number {
  return (pixels[at]! << 16) | (pixels[at + 1]! << 8) | pixels[at + 2]!
}

/**
 * Writes the color `packed` holds as red, green, and blue bytes as a hex.
 */
export function colorOf(packed: number): string {
  return `#${packed.toString(16).padStart(6, '0')}`
}

/**
 * Rewrites every pixel of `source` into `target` in `palette`, each color of
 * the room found by its place in `shades`, light to dark, and set to the shade
 * the palette gives that color.
 */
export function recolor(
  palette : string,
  shades  : readonly number[],
  source  : Uint8ClampedArray,
  target  : Uint8ClampedArray
): void {
  const last = shades.length - 1
  const to   = shades.map((_, color) => shades[Math.min(last, Number(palette[last - color]))]!)
  for (let at = 0; at < source.length; at += 4) {
    const next     = to[Math.max(0, shades.indexOf(packedAt(source, at)))]!
    target[at]     = next >> 16
    target[at + 1] = (next >> 8) & 255
    target[at + 2] = next & 255
    target[at + 3] = 255
  }
}

/**
 * Finds the colors `pixels` holds, at most as many as the Game Boy's shades,
 * from the lightest to the darkest.
 *
 * Returns:
 *   Each color's red, green, and blue bytes as one number.
 */
export function shadesOf(pixels: Uint8ClampedArray): number[] {
  const colors = new Set<number>()
  for (let at = 0; at < pixels.length; at += 4) colors.add(packedAt(pixels, at))
  return [...colors].toSorted((a, b) => lightness(b) - lightness(a)).slice(0, spriteShades.length)
}
