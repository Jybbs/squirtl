import type { MaybeElementRef }     from '@vueuse/core'
import { type Ref, onMounted, ref } from 'vue'

import { RoomImages }                from '../../game/images.ts'
import { GameScreen, SCREEN }        from '../../game/screen.ts'
import { type Canvas, useFrameLoop } from '../../widgets/frames.ts'
import { stepText }                  from '../../widgets/numbers.ts'
import { type Scrub, useScrub }      from '../../widgets/scrub.ts'
import * as sees                     from '../sees.ts'

/**
 * The play of the widget's episode beside the slider its gray frames make of
 * the episode's steps.
 */
export interface Staging {
  scrub : Scrub
  stage : Playthrough
}

/**
 * The pace the widget plays its episode at, the milliseconds between two
 * presses and the milliseconds it rests on the starter before playing again.
 */
export const SEES_TEMPO = { beat: 140, rest: 3600 }

/**
 * The name a screen reader reads for the gray frames the widget's slider runs
 * along.
 */
const SLIDER = 'The episode’s steps, which hold the observation at the step they point to'

/**
 * The play of one episode and the canvases it draws into, the screen a player
 * sees gliding between squares beside the observation the network reads, which
 * drops into its canvases once a step's glide lands, or at the next press.
 */
export class Playthrough {
  readonly flagged     : Ref<boolean[]>
  readonly frames      : Canvas[] = Array.from({ length: sees.OBSERVING.stack }, () => ref())
  readonly grid        : Canvas   = ref()
  readonly images      = new RoomImages()
  readonly last        = sees.stepsOf()
  readonly observation : sees.Observation
  readonly screen      : Canvas   = ref()
  readonly step        = ref(0)

  readonly #network : GameScreen
  readonly #shown   : GameScreen
  readonly #wake    : () => void
  #pending          = false
  #pixels           : ImageData[] = []
  #screen!          : CanvasRenderingContext2D
  #source!          : CanvasRenderingContext2D

  constructor(wake: () => void) {
    this.observation = new sees.Observation(() => {
      this.#network.snap()
      this.#network.draw(this.#source)
      return this.#source.getImageData(0, 0, SCREEN.width, SCREEN.height).data
    })
    this.flagged  = ref(this.observation.flagged)
    this.#network = new GameScreen(this.observation.player.episode, this.images)
    this.#shown   = new GameScreen(this.observation.player.episode, this.images)
    this.#wake    = wake
  }

  /**
   * Puts the gray frames, the oldest first, and the grid on their canvases and
   * shows the flags and the step they were read at.
   */
  #paint(): void {
    const canvases = [...this.frames, this.grid]
    this.#pending  = false
    for (const i of this.frames.keys()) {
      sees.paintFrame(this.observation.frame(this.frames.length - 1 - i), this.#pixels[i]!.data)
    }
    sees.paintGrid(this.observation.grid, this.#pixels.at(-1)!.data)
    for (const [i, canvas] of canvases.entries()) {
      canvas.value!.getContext('2d')!.putImageData(this.#pixels[i]!, 0, 0)
    }
    this.flagged.value = this.observation.flagged
    this.step.value    = this.observation.player.episode.steps
  }

  /**
   * Moves the screen's glide on by `elapsed` milliseconds and draws it, putting
   * the step's observation on its canvases once the glide lands, and reports
   * whether the screen still moves.
   */
  advance(elapsed: number): boolean {
    const moving = this.#shown.advance(elapsed)
    this.#shown.draw(this.#screen)
    if (!moving && this.#pending) this.#paint()
    return moving
  }

  /**
   * Plays the episode again to step `to` and shows it at once, fading the
   * screen in where `fade` is set.
   */
  jump(to: number, fade = false): void {
    this.observation.seek(to)
    this.#shown.snap(fade)
    this.#shown.draw(this.#screen)
    this.#paint()
    this.#wake()
  }

  /**
   * Takes the mounted canvases' contexts and image data, beside a canvas of the
   * screen's size no reader sees, and shows the step once the rooms load.
   */
  mount(): void {
    const source = Object.assign(document.createElement('canvas'), SCREEN)
    this.#pixels = [...this.frames, this.grid].map(({ value }) => new ImageData(value!.width, value!.height))
    this.#screen = this.screen.value!.getContext('2d')!
    this.#source = source.getContext('2d', { willReadFrequently: true })!
    this.images.whenReady(() => this.jump(this.step.value))
  }

  /**
   * Presses once and starts the screen's glide to Blue's square, first putting
   * the last step's observation on its canvases where its glide has not landed.
   */
  tick(): void {
    if (this.#pending) this.#paint()
    this.observation.next()
    this.#shown.follow(SEES_TEMPO.beat)
    this.#pending = true
    this.#wake()
  }
}

/**
 * Plays one episode a press at a time while the widget at `root` shows on
 * screen, drawing its screen on every frame while it glides, and makes the gray
 * frames the slider over its steps, which holds the observation at the step
 * they point to.
 */
export function usePlaythrough(root: MaybeElementRef): Staging {
  const stage = new Playthrough(() => wake())
  onMounted(() => stage.mount())

  const wake  = useFrameLoop(stage.screen, elapsed => stage.advance(elapsed))
  const scrub = useScrub(root, {
    beat    : SEES_TEMPO.beat,
    done    : () => stage.observation.player.done,
    finish  : () => stage.jump(stage.last),
    rest    : SEES_TEMPO.rest,
    restart : () => stage.jump(0, true),
    tick    : () => stage.tick()
  }, {
    at       : stage.step,
    count    : stage.last + 1,
    describe : at => stepText(at, stage.last),
    label    : SLIDER,
    seek     : to => stage.jump(to)
  })

  return { scrub, stage }
}
