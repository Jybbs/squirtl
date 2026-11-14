/**
 * Declares the part of `gifenc` the README's preview calls, since the package
 * ships its JavaScript with no declarations of its own.
 */
declare module 'gifenc' {
  /**
   * A color's red, green, and blue bytes.
   */
  type Color = readonly number[]

  /**
   * How one frame is written: the milliseconds it holds, its disposal method,
   * the palette the first frame sets for every frame, and the palette index
   * left clear.
   */
  interface FrameOptions {
    delay?            : number
    dispose?          : number
    palette?          : readonly Color[]
    transparent?      : boolean
    transparentIndex? : number
  }

  /**
   * A GIF written frame by frame into a growing buffer.
   */
  interface Encoder {
    bytes(): Uint8Array
    finish(): void
    writeFrame(index: Uint8Array, width: number, height: number, options?: FrameOptions): void
  }

  /**
   * Opens a GIF whose first frame writes its header, its global palette, and
   * a loop that repeats forever.
   */
  export function GIFEncoder(): Encoder

  /**
   * Finds the index of the color of `colors` closest to `pixel`, the earliest
   * of those as close.
   */
  export function nearestColorIndex(colors: readonly Color[], pixel: Color): number
}
