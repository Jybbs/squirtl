import { clamp } from '@vueuse/core'

import SETTINGS                  from '../rendered/settings.json' with { type: 'json' }
import { type PlotLabel, round } from '../drawing/plot.ts'
import { Episode, type Term }    from '../game/episode.ts'
import { autoPress }             from '../game/player.ts'
import { seeded }                from '../game/random.ts'
import { IDENTITY }              from '../identity/identity.ts'
import { count, fixed }          from '../widgets/numbers.ts'

/**
 * One payment of an episode that jumps its return, a milestone's or the
 * starter's, by the steps from the episode's start until it arrives.
 */
interface Arrival {
  ahead : number
  term  : Exclude<Term, 'novelty'>
}

/**
 * An episode the widget weighs, under the name its key reads, the steps it
 * took, the payments that jump its return, and the step it reached the starter
 * on, `Infinity` where it never did.
 */
export interface Weighed {
  arrivals : readonly Arrival[]
  name     : string
  player   : 'agent' | 'random'
  starter  : number
  steps    : number
  told     : string
}

/**
 * A run of tiles in the lane along the chart's top, the tiles of payments a few
 * pixels apart on the curve sharing one leader, which runs from the middle of
 * the tiles, through a comb joining them where they are several, down to the
 * curve at the steps their payments average on the log scale.
 */
interface TileGroup {
  leader : string
  tiles  : readonly { arrival: Arrival, x: number }[]
}

/**
 * The chart laid out at one width for one discount: its gridlines and labels,
 * the weight curve, the half point and its label, each named discount's stop
 * on the half line, each episode's tile groups in the lane, and each payment's
 * dot on the curve.
 */
export interface WeightPlot {
  curve  : string
  dots   : readonly { player: Weighed['player'], term: Arrival['term'], x: number, y: number }[]
  floor  : number
  grid   : string
  half   : { label: PlotLabel, x: number, y: number }
  labels : readonly PlotLabel[]
  lanes  : readonly { groups: readonly TileGroup[], player: Weighed['player'] }[]
  stops  : readonly number[]
  width  : number
}

/**
 * The discount the agent's settings declare, and the named discounts a drag
 * catches as it passes, the setting between 0.99 and 0.999.
 */
export const DISCOUNT = SETTINGS.agent.discount
export const NAMED    = [0.99, DISCOUNT, 0.999] as const

/**
 * The chart's height, the room it leaves on each side, the longest episode on
 * its log scale and the steps it labels, the positions of the half point a
 * slider steps through and the half lives they span, the tile a payment takes
 * in the lane and its pitch, and the lane's top.
 */
export const WEIGHING = {
  ahead  : [1, 10, 100, 1000, 10000],
  halves : [50, 3000],
  height : 356,
  lane   : 6,
  limit  : SETTINGS.environment.max_episode_steps,
  pitch  : 26,
  stops  : 160,
  tile   : 22,
  box    : { bottom: 52, left: 44, right: 20, top: 56 }
} as const

/**
 * The log of the longest episode, the span of the chart's scale.
 */
const SPAN = Math.log10(WEIGHING.limit)

/**
 * Reads the steps ahead at which a payment counts half under `discount`.
 */
export const halfLife = (discount: number): number => Math.log(0.5) / Math.log(discount)

/**
 * Spells `discount` as the settings write it where it is a named one, and to
 * four places otherwise.
 */
export const spelled = (discount: number): string =>
  NAMED.includes(discount as never) ? String(discount) : fixed(discount, 4)

/**
 * Reads the position of the half point a slider stands at for `discount`.
 */
export const stopOf = (discount: number): number =>
  Math.round(Math.log10(halfLife(discount)) / SPAN * WEIGHING.stops)

/**
 * Reads what the starter counts under `discount` once it arrives `ahead` steps
 * from the start.
 */
export const weightOf = (discount: number, ahead: number): number =>
  SETTINGS.reward.goal * discount ** ahead

/**
 * Reads the discount the half point at `stop` sets, its half life kept within
 * the range the chart reads and caught by each named discount as it passes.
 */
export function discountAt(stop: number): number {
  const half  = clamp(10 ** (stop / WEIGHING.stops * SPAN), WEIGHING.halves[0], WEIGHING.halves[1])
  const named = NAMED.find(each => Math.abs(Math.log10(halfLife(each)) - Math.log10(half)) < 0.035)
  return named ?? 0.5 ** (1 / half)
}

/**
 * Plays one episode of the model of the first rooms from `seed`, the agent's
 * stand-in walking the shortest way after `wander` random presses, and records
 * every payment that jumps its return.
 */
export function weighed(name: string, player: Weighed['player'], wander: number, seed: number): Weighed {
  const episode  = new Episode()
  const random   = seeded(seed)
  const arrivals = [] as Arrival[]

  while (!episode.done) {
    for (const { term } of episode.press(autoPress(episode, random, wander))) {
      if (term !== 'novelty') arrivals.push({ ahead: episode.steps, term })
    }
  }
  const starter = arrivals.find(each => each.term === 'goal')?.ahead ?? Infinity
  const reach   = starter === Infinity ? 'never reaching the starter' : `to the starter in ${count(starter)} steps`
  return { arrivals, name, player, starter, steps: episode.steps, told: `${name} ${reach}` }
}

/**
 * The agent's stand-in walking to the starter, and random presses wandering
 * to it from the first seed past the walk's under which they reach it.
 */
export const EPISODES: readonly Weighed[] = [
  weighed('The walk', 'agent', 90, 1000),
  weighed('A wander', 'random', Infinity, 1001)
]

/**
 * Lays the chart out at `width` pixels for `discount`.
 */
export function plotOf(discount: number, width: number, episodes: readonly Weighed[] = EPISODES): WeightPlot {
  const { box, height } = WEIGHING
  const floor = height - box.bottom
  const end   = width - box.right
  const x     = (ahead: number) => round(box.left + (end - box.left) * Math.log10(Math.max(1, ahead)) / SPAN)
  const y     = (weight: number) => round(box.top + (floor - box.top) * (1 - weight))
  const half  = halfLife(discount)
  const right = x(half) < width - 200

  return {
    curve : Array.from({ length: WEIGHING.stops + 1 }, (_, n) => {
      const ahead = 10 ** (SPAN * n / WEIGHING.stops)
      return `${n === 0 ? 'M' : 'L'}${x(ahead)},${y(discount ** ahead)}`
    }).join(''),
    dots : episodes.flatMap(({ arrivals, player }) => arrivals.map(({ ahead, term }) =>
      ({ player, term, x: x(ahead), y: y(discount ** ahead) }))),
    floor : floor,
    grid  : [0, 0.5, 1].map(weight => `M${box.left},${y(weight)}H${end}`).join(''),
    half  : {
      x     : x(half),
      y     : y(0.5),
      label : {
        anchor : right ? 'start' : 'end',
        text   : `Half its weight at ${count(Math.round(half))} steps`,
        x      : x(half) + (right ? 14 : -14),
        y      : y(0.5) - 12
      }
    },
    labels : [
      ...[0, 0.5, 1].map(weight => ({ anchor: 'end', text: fixed(weight, 1), x: box.left - 8, y: y(weight) + 4 }) as const),
      ...WEIGHING.ahead.map((ahead, n) => ({
        anchor : n === 0 ? 'start' : n === WEIGHING.ahead.length - 1 ? 'end' : 'middle',
        text   : count(ahead),
        x      : x(ahead),
        y      : floor + 20
      }) as const)
    ],
    lanes : lanesOf(episodes, x, width).map(({ groups, player }) => ({
      player : player,
      groups : groups.map(({ ahead, tiles, x: middle }) => ({ leader: leaderOf(tiles, middle, x(ahead), y(discount ** ahead) - 6), tiles }))
    })),
    stops : NAMED.map(each => x(halfLife(each))),
    width : width
  }
}

/**
 * Draws the leader from `tiles`, whose middle is `middle`, down to the point
 * (`x`, `y`) on the curve, through a comb beneath the tiles where they are
 * several.
 */
function leaderOf(tiles: TileGroup['tiles'], middle: number, x: number, y: number): string {
  const below = WEIGHING.lane + WEIGHING.tile
  const comb  = below + 5
  const teeth = tiles.length > 1 ? `M${tiles[0]!.x},${comb}H${tiles.at(-1)!.x}${tiles.map(each => `M${each.x},${below}V${comb}`).join('')}` : ''
  return `${teeth}M${middle},${tiles.length > 1 ? comb : below}L${x},${round(y)}`
}

/**
 * Sets each episode's tiles in one row of the lane centered over its payments,
 * the rows kept a pitch apart and inside the chart so the tiles hold still
 * while the curve moves, and groups the tiles of payments under eight pixels
 * apart on the curve under one leader.
 */
function lanesOf(episodes: readonly Weighed[], x: (ahead: number) => number, width: number) {
  const { box, pitch, tile } = WEIGHING
  const rows = episodes.map(episode => {
    const span = episode.arrivals.length * pitch - (pitch - tile)
    const mean = episode.arrivals.reduce((sum, each) => sum + x(each.ahead), 0) / episode.arrivals.length
    return { episode, left: mean - span / 2, span }
  })

  rows.forEach((row, n) => { if (n > 0) row.left = Math.max(row.left, rows[n - 1]!.left + rows[n - 1]!.span + pitch) })
  let limit = width - box.right
  for (const row of rows.toReversed()) {
    row.left = Math.min(row.left, limit - row.span)
    limit    = row.left - pitch
  }

  return rows.map(({ episode, left }) => {
    const start  = Math.max(left, box.left)
    const groups = [] as { tiles: { arrival: Arrival, x: number }[] }[]

    episode.arrivals.forEach((arrival, n) => {
      const placed = { arrival, x: round(start + n * pitch + tile / 2) }
      const last   = groups.at(-1)
      if (last && x(arrival.ahead) - x(last.tiles[0]!.arrival.ahead) < 8) last.tiles.push(placed)
      else groups.push({ tiles: [placed] })
    })
    return {
      player : episode.player,
      groups : groups.map(({ tiles }) => ({
        ahead : 10 ** (tiles.reduce((sum, each) => sum + Math.log10(each.arrival.ahead), 0) / tiles.length),
        tiles : tiles,
        x     : round(tiles.reduce((sum, each) => sum + each.x, 0) / tiles.length)
      }))
    }
  })
}

/**
 * The width a drawing of the chart takes at least, and the identity's strokes
 * it draws in.
 */
export const LEAST   = 280
export const STROKES = IDENTITY.lengths.strokes
