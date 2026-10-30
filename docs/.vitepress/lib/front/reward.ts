import { termMark }             from '../game/actors.ts'
import * as episode             from '../game/episode.ts'
import { RoomImages }           from '../game/images.ts'
import { Player, type Playing } from '../game/player.ts'
import { GameScreen }           from '../game/screen.ts'
import type * as autoplay       from '../widgets/autoplay.ts'
import type { ChipContent }     from '../widgets/chips.ts'
import * as numbers             from '../widgets/numbers.ts'

/**
 * The figures the widget shows at one step: the return so far, the step out of
 * the episode's steps, what the step's press paid, and what each term has paid
 * so far.
 */
export interface Figures {
  paid  : ChipContent
  step  : string
  terms : readonly ChipContent[]
  total : string
}

/**
 * A payment that jumps the return, a milestone's or the starter's, beside the
 * return it reaches.
 */
export interface Jump {
  term  : Exclude<episode.Term, 'novelty'>
  total : number
}

/**
 * The episode the widget shows: the player pressing it, the screen showing it
 * beside the images of the rooms the screen draws, and its every step recorded,
 * which the climb and the figures read at any step.
 */
export interface Showing {
  images : RoomImages
  player : Player
  screen : GameScreen
  trace  : readonly Traced[]
}

/**
 * How the widget plays its episode, in milliseconds: the beat between two
 * presses and the beat while Oak leads Blue, the glide of one step, and the
 * rest on the starter before the episode plays again.
 */
export interface Tempo {
  beat  : number
  glide : number
  lead  : number
  rest  : number
}

/**
 * One step of the episode the widget plays, recorded once its press ends: the
 * flags set, the jumps the press made, whether Oak leads Blue, what the press
 * paid, the squares reached, and what each term and the whole return have paid.
 */
export interface Traced {
  flags   : readonly episode.Flag[]
  jumps   : readonly Jump[]
  led     : boolean
  paid    : readonly episode.Paid[]
  reached : number
  shares  : Readonly<Record<episode.Term, number>>
  total   : number
}

/**
 * The name the chip of the last press takes, by what the press paid or, where
 * it paid nothing, by where the episode stands.
 */
const PAID = {
  following  : 'Following Oak',
  milestone  : 'A milestone',
  milestones : 'Two milestones',
  nothing    : 'Already reached',
  novelty    : 'A new position',
  starter    : 'The starter',
  waking     : 'Blue wakes'
}

/**
 * The decimal places each figure takes, the places a new position's payment
 * fills.
 */
const PLACES = 5

/**
 * The note the starter's chip takes before and once Blue chooses it, Squirtle
 * being the starter in the Poké Ball the agent's stand-in walks up to.
 */
const STARTER = { chosen: 'Squirtle', waiting: 'Not yet' }

/**
 * The pace the widget plays its episode at.
 */
export const TEMPO: Tempo = { beat: 120, glide: 110, lead: 170, rest: 3600 }

/**
 * Each term's name on a widget.
 */
const TERM_LABELS: Readonly<Record<episode.Term, string>> = {
  milestone : 'Milestones',
  novelty   : 'New positions',
  starter   : 'The starter'
}

/**
 * The reward's terms in the order of what one press of each pays, the least
 * first.
 */
export const terms: readonly episode.Term[] = (Object.keys(episode.EPISODE.pay) as episode.Term[])
  .toSorted((left, right) => episode.EPISODE.pay[left] - episode.EPISODE.pay[right])

/**
 * The game's mark for each term, drawn once as the module loads.
 */
export const marks = Object.fromEntries(terms.map(term => [term, termMark(term)])) as Readonly<
  Record<episode.Term, string>
>

/**
 * Reads the chip of the press that ended the step `at`, marked by the term that
 * paid the most, two milestones paid together named as such.
 */
function paidChip(traced: Traced, at: number): ChipContent {
  const lead       = traced.paid.toSorted((left, right) => right.pay - left.pay)[0]?.term
  const milestones = traced.paid.filter(item => item.term === 'milestone').length
  const named      = lead === 'milestone' && milestones > 1 ? PAID.milestones : lead && PAID[lead]
  const resting    = at === 0 ? PAID.waking : traced.led ? PAID.following : PAID.nothing
  return {
    mark  : lead ? marks[lead] : '',
    name  : named ?? resting,
    note  : null,
    role  : lead ?? 'none',
    value : numbers.signed(traced.paid.reduce((sum, item) => sum + item.pay, 0), PLACES)
  }
}

/**
 * Records the step the last press of `player` ended on, beside the jumps
 * `jumps` the press made.
 */
function recorded(player: Player, jumps: readonly Jump[]): Traced {
  const { flags, reached, script, shares, total } = player.episode
  return {
    flags   : [...flags],
    jumps   : jumps,
    led     : script.length > 0,
    paid    : player.paid,
    reached : reached.size,
    shares  : { ...shares },
    total   : total
  }
}

/**
 * Writes the note each term's chip takes at the step `traced` records: the new
 * positions as their count times what each pays, the milestones reached of all
 * of them, and the starter once chosen.
 */
function termNotes(settings: episode.EpisodeSettings, traced: Traced): Record<episode.Term, string> {
  const met = traced.flags.filter(flag => episode.milestones.includes(flag)).length
  return {
    milestone : `${met} of ${episode.milestones.length}`,
    novelty   : `${numbers.count(traced.reached - 1)} × ${numbers.fixed(settings.pay.novelty, PLACES)}`,
    starter   : traced.flags.includes('starter') ? STARTER.chosen : STARTER.waiting
  }
}

/**
 * Describes the step `at` of `trace` for a screen reader, the step out of the
 * episode's steps and the return so far.
 */
export function describeStep(trace: readonly Traced[], at: number): string {
  return `${numbers.stepText(at, trace.length - 1)}, the return ${numbers.fixed(trace[at]!.total, PLACES)}`
}

/**
 * Reads the figures the widget shows at the step `at` of `trace`.
 */
export function figuresAt(
  trace    : readonly Traced[],
  at       : number,
  settings : episode.EpisodeSettings = episode.EPISODE
): Figures {
  const traced = trace[at]!
  const notes  = termNotes(settings, traced)
  return {
    paid  : paidChip(traced, at),
    step  : numbers.stepText(at, trace.length - 1),
    total : numbers.fixed(traced.total, PLACES),
    terms : terms.map(term => ({
      mark  : marks[term],
      name  : TERM_LABELS[term],
      note  : notes[term],
      role  : term,
      value : numbers.fixed(traced.shares[term], PLACES)
    }))
  }
}

/**
 * Lists the entries of the widget's key of terms, each term in its hue beside
 * what one press of it pays, and a square already reached paying nothing.
 */
export function keyTerms(settings: episode.EpisodeSettings = episode.EPISODE): ChipContent[] {
  const paying = terms.map((term): ChipContent => ({
    mark  : marks[term],
    name  : TERM_LABELS[term],
    note  : null,
    role  : term,
    value : numbers.signed(settings.pay[term], PLACES)
  }))
  return [
    ...paying,
    { mark: '', name: PAID.nothing, note: null, role: 'none', value: numbers.signed(0, PLACES) }
  ]
}

/**
 * Plays `player`'s episode through an autoplay at `tempo`, a press each beat
 * and a longer beat while Oak leads Blue, the episode again from the bedroom
 * once it has rested on its end, and its end at once where motion is off,
 * calling `show` after each with the milliseconds the screen glides over.
 */
export function playingOf(
  player : Player,
  show   : (span: number) => void,
  tempo  : Tempo = TEMPO
): autoplay.Ticking {
  return {
    beat : () => player.episode.script.length > 0 ? tempo.lead : tempo.beat,
    done : () => player.done,
    rest : tempo.rest,

    finish: () => {
      player.finish()
      show(0)
    },

    restart: () => {
      player.reset()
      show(0)
    },

    tick: () => {
      player.next()
      show(tempo.glide)
    }
  }
}

/**
 * Sets up the episode a player pressing as `playing` sets plays, its screen
 * drawing the rooms `images` loads, and its every step recorded.
 */
export function showingOf(images: RoomImages = new RoomImages(), playing: Partial<Playing> = {}): Showing {
  const player = new Player(playing)
  return { images, player, screen: new GameScreen(player.episode, images), trace: traceOf(playing) }
}

/**
 * Records every step of the episode a player pressing as `playing` sets plays,
 * from Blue waking to its end.
 */
export function traceOf(playing: Partial<Playing> = {}): Traced[] {
  const player = new Player(playing)
  const trace  = [recorded(player, [])]
  while (!player.done) {
    let total   = player.episode.total
    const paid  = player.next()
    const jumps = paid.flatMap((item): Jump[] => {
      total += item.pay
      return item.term === 'novelty' ? [] : [{ term: item.term, total }]
    })
    trace.push(recorded(player, jumps))
  }
  return trace
}
