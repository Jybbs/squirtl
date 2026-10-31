import { clamp } from '@vueuse/core'

import { type Scheme, hexOf } from '../identity/identity.ts'
import { seeded }             from '../game/random.ts'

/**
 * One side path off the reader's walk, the step of the walk it leaves from and
 * the squares it wanders through.
 */
export interface Branch {
  at     : number
  points : readonly SkyPoint[]
}

/**
 * A region of the page holding words, behind which the walks dim.
 */
interface Quiet {
  bottom : number
  left   : number
  right  : number
  top    : number
}

/**
 * What one frame of the splash draws from, the page's width and height, the
 * viewport's top and height, the regions holding words, the seconds the walk
 * has flickered for, and whether motion plays.
 */
export interface Scene {
  height : number
  quiet  : readonly Quiet[]
  scroll : number
  still  : boolean
  time   : number
  view   : number
  width  : number
}

/**
 * The tuning of the splash: the side of a square, the gap between the rows the
 * walk snakes along, the top of its first row, the steps between two side paths
 * at each width and the page's width below which they thin out, how far down
 * the viewport the walk's head runs as a share of its height, the share of its
 * way to that step the head moves each second, how far past each region of
 * words the walks dim, and how much they dim there.
 */
export interface Sky {
  every  : { narrow: number, wide: number }
  follow : number
  lead   : number
  margin : number
  narrow : number
  pitch  : number
  quiet  : number
  row    : number
  top    : number
}

/**
 * The center of one square of the page's grid, in CSS pixels from the top left
 * of the page.
 */
export type SkyPoint = readonly [x: number, y: number]

/**
 * The colors one scheme draws the walks in, the trail's dots, the head and the
 * steps just taken, each a hex from the identity.
 */
export interface Tones {
  dot    : string
  strong : string
}

/**
 * The splash's tuning.
 */
export const SKY: Sky = {
  every  : { narrow: 5, wide: 3 },
  follow : 3,
  lead   : 0.6,
  margin : 16,
  narrow : 600,
  pitch  : 14,
  quiet  : 0.3,
  row    : 104,
  top    : 60
}

/**
 * The colors each scheme draws the walks in, Denim's dots under a head in the
 * ramp's step that stands out most from the ground.
 */
export const TONES: Readonly<Record<Scheme, Tones>> = {
  dark  : { dot: hexOf('primary'), strong: hexOf('pale') },
  light : { dot: hexOf('primary'), strong: hexOf('deep') }
}

/**
 * Reads a value between 0 and 1 that `a` and `b` always give alike, from which
 * each dot takes the rate and the phase of its flicker.
 */
const hashed = (a: number, b: number): number => {
  const x = Math.sin(a * 127.1 + b * 311.7) * 43758.5453
  return x - Math.floor(x)
}

/**
 * Reports whether `point` on the page falls within ten pixels of the viewport,
 * where its dot shows.
 */
function onScreen(point: SkyPoint, scene: Pick<Scene, 'scroll' | 'view'>): boolean {
  const shown = point[1] - scene.scroll
  return shown >= -10 && shown <= scene.view + 10
}

/**
 * Paints one dot of a walk at `point` on the page at `alpha` and `radius`,
 * dimmed behind words.
 */
function paintDot(
  context : Pick<CanvasRenderingContext2D, 'arc' | 'beginPath' | 'fill' | 'globalAlpha'>,
  alpha   : number,
  point   : SkyPoint,
  radius  : number,
  scene   : Pick<Scene, 'quiet' | 'scroll'>,
  sky     : Sky
): void {
  const [x, y] = point
  let dim      = 1
  for (const zone of scene.quiet) {
    if (x > zone.left && x < zone.right && y > zone.top && y < zone.bottom) dim = sky.quiet
  }
  context.globalAlpha = alpha * dim
  context.beginPath()
  context.arc(x, y - scene.scroll, radius, 0, Math.PI * 2)
  context.fill()
}

/**
 * Lays out the side paths branching off `walk`, one every few steps, each
 * wandering away from the walk's row and back across it for a seeded number of
 * squares.
 */
export function branchesOf(walk: readonly SkyPoint[], width: number, sky: Sky = SKY): Branch[] {
  const branches: Branch[] = []
  for (let i = 4; i < walk.length; i += width < sky.narrow ? sky.every.narrow : sky.every.wide) {
    const random             = seeded(i * 31 + 5)
    let [x, y]               = walk[i]!
    const points: SkyPoint[] = [[x, y]]
    const length             = 6 + Math.floor(random() * 18)
    const away               = random() < 0.5 ? -1 : 1
    for (let step = 0; step < length; step++) {
      if (random() < 0.55) y += away * sky.pitch
      else x += (random() < 0.5 ? -1 : 1) * sky.pitch
      points.push([clamp(x, sky.pitch / 2, width - sky.pitch / 2), y])
    }
    branches.push({ at: i, points })
  }
  return branches
}

/**
 * Reads how strongly a dot shows at `time`, which drifts between 0.72 and 1 at
 * a rate and a phase its two indices fix, and holds at 1 while motion is off.
 */
export function flicker(scene: Pick<Scene, 'still' | 'time'>, i: number, j: number): number {
  const wave = Math.sin(scene.time * (1.1 + hashed(i, j) * 1.7) + hashed(j, i) * 6.283)
  return scene.still ? 1 : 0.72 + 0.28 * (0.5 + 0.5 * wave)
}

/**
 * Finds the step of `walk` the reader has scrolled to, the one level with a
 * point `lead` of the way down the viewport, as a share of the walk.
 */
export function headOf(
  walk  : readonly SkyPoint[],
  scene : Pick<Scene, 'height' | 'scroll' | 'view'>,
  sky   : Sky = SKY
): number {
  return clamp((scene.scroll + scene.view * sky.lead) / scene.height, 0, 1) * walk.length
}

/**
 * Paints one frame of the splash: every side path the walk's head has passed,
 * grown and faded by how long ago it passed, then the walk up to its head, its
 * newest steps larger and stronger, each dot dimmed behind words and skipped
 * where it falls outside the viewport.
 */
export function paintSky(
  context  : Pick<CanvasRenderingContext2D, 'arc' | 'beginPath' | 'fill' | 'fillStyle' | 'globalAlpha'>,
  branches : readonly Branch[],
  head     : number,
  scene    : Scene,
  tones    : Tones,
  walk     : readonly SkyPoint[],
  sky      : Sky = SKY
): void {
  const reached = Math.floor(scene.still ? walk.length : head)

  context.fillStyle = tones.dot
  for (const branch of branches) {
    if (branch.at > reached) break
    const age   = scene.still ? 0.5 : Math.min(1, (reached - branch.at) / 260)
    const grown = scene.still
                ? branch.points.length
                : Math.min(branch.points.length, Math.floor((reached - branch.at) / 2) + 1)
    for (let s = 1; s < grown; s++) {
      const point = branch.points[s]!
      if (!onScreen(point, scene)) continue
      const alpha = (0.55 - 0.25 * age) * (1 - 0.7 * s / branch.points.length) * flicker(scene, branch.at, s)
      paintDot(context, alpha, point, 1.7, scene, sky)
    }
  }
  for (let i = 0; i < reached; i++) {
    const point       = walk[i]!
    const recent      = 1 - Math.min(1, (reached - i) / 120)
    context.fillStyle = recent > 0.9 ? tones.strong : tones.dot
    if (!onScreen(point, scene)) continue
    paintDot(context, (0.09 + 0.32 * recent) * flicker(scene, i, 3), point, 1.7 + 2 * recent, scene, sky)
  }
  if (!scene.still && walk[reached]) {
    context.fillStyle = tones.strong
    if (onScreen(walk[reached], scene)) paintDot(context, 0.7, walk[reached], 5, scene, sky)
  }
  context.globalAlpha = 1
}

/**
 * Places each box of words `boxes` holds on the page, `scroll` being the
 * viewport's top, widened on every side by the margin the walks dim across.
 */
export function quietOf(boxes: readonly Quiet[], scroll: number, sky: Sky = SKY): Quiet[] {
  return boxes.map(box => ({
    bottom : box.bottom + scroll + sky.margin,
    left   : box.left - sky.margin,
    right  : box.right + sky.margin,
    top    : box.top + scroll - sky.margin
  }))
}

/**
 * Lays out the reader's walk as a serpentine of rows down the page, each row
 * running the page's width a square at a time, drifting a square up or down at
 * seeded steps, the walk turning down at each row's end to the next row and
 * running it the other way.
 */
export function serpentine(width: number, height: number, sky: Sky = SKY): SkyPoint[] {
  const columns          = Math.floor(width / sky.pitch)
  const rows             = Math.max(1, Math.floor((height - sky.top) / sky.row))
  const walk: SkyPoint[] = []
  for (let k = 0; k < rows; k++) {
    const random             = seeded(k * 131 + 7)
    const points: SkyPoint[] = []
    let row                  = 0
    for (let c = 0; c < columns; c++) {
      if (random() < 0.32) row = clamp(row + (random() < 0.5 ? -1 : 1), -2, 2)
      points.push([c * sky.pitch + sky.pitch / 2, sky.top + k * sky.row + row * sky.pitch])
    }
    const ordered = k % 2 ? points.toReversed() : points
    const last    = walk.at(-1)
    if (last) for (let y = last[1] + sky.pitch; y < ordered[0]![1]; y += sky.pitch) walk.push([last[0], y])
    walk.push(...ordered)
  }
  return walk
}
