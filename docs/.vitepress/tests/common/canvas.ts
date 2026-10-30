import { vi } from 'vitest'

/**
 * One circle a drawing filled, beside the fill and the opacity it took.
 */
export interface Arc {
  alpha  : number
  fill   : string
  radius : number
  x      : number
  y      : number
}

/**
 * One rectangle a drawing filled, beside the fill and the opacity it took.
 */
export interface Mark {
  alpha  : number
  fill   : string
  height : number
  width  : number
  x      : number
  y      : number
}

/**
 * A stand-in for a canvas's 2D context, which happy-dom leaves undrawn, that
 * records every circle and rectangle a drawing fills, every image it draws, and
 * every view it puts, in order, a clear emptying the circles and the rectangles,
 * and that reads every view back blank.
 */
export class Recorder {
  arcs                  : Arc[]                                 = []
  fillStyle             : CanvasRenderingContext2D['fillStyle'] = ''
  globalAlpha           = 1
  imageSmoothingEnabled = true
  marks                 : Mark[]                                = []

  readonly images : unknown[][] = []
  readonly views  : ImageData[] = []

  #path: Pick<Arc, 'radius' | 'x' | 'y'> | null = null

  /**
   * Sets the circle the next fill draws.
   */
  arc(x: number, y: number, radius: number): void {
    this.#path = { radius, x, y }
  }

  /**
   * Starts a path with no circle on it.
   */
  beginPath(): void {
    this.#path = null
  }

  /**
   * Empties the circles and the rectangles recorded so far.
   */
  clearRect(): void {
    this.arcs  = []
    this.marks = []
  }

  /**
   * Makes a blank view of `width` by `height` pixels.
   */
  createImageData(width: number, height: number): ImageData {
    return { data: new Uint8ClampedArray(width * height * 4), height, width } as ImageData
  }

  /**
   * Records the image and every argument after it.
   */
  drawImage(...args: unknown[]): void {
    this.images.push(args)
  }

  /**
   * Records the circle the path holds beside the fill and the opacity set.
   */
  fill(): void {
    if (this.#path) this.arcs.push({ ...this.#path, alpha: this.globalAlpha, fill: String(this.fillStyle) })
  }

  /**
   * Records the rectangle beside the fill and the opacity set.
   */
  fillRect(x: number, y: number, width: number, height: number): void {
    this.marks.push({ alpha: this.globalAlpha, fill: String(this.fillStyle), height, width, x, y })
  }

  /**
   * Reads a blank view of `width` by `height` pixels back.
   */
  getImageData(_left: number, _top: number, width: number, height: number): ImageData {
    return this.createImageData(width, height)
  }

  /**
   * Records the view put onto the canvas.
   */
  putImageData(image: ImageData): void {
    this.views.push(image)
  }

  /**
   * Takes a transform and records nothing, since every position a case reads is
   * the one the drawing passed.
   */
  setTransform(): void {}
}

/**
 * Has every canvas a case mounts draw into `context`, or give no context where
 * it is `null`, and returns `context`.
 */
export function drawInto<C extends Recorder | null>(context: C): C {
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(context as never)
  return context
}
