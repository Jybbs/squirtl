import SETTINGS           from '../rendered/settings.json' with { type: 'json' }
import { seeded }         from '../game/random.ts'
import { count, counted } from '../widgets/numbers.ts'

/**
 * One episode of the made-up run, the step the run stands at once it ends and
 * whether it reached the starter.
 */
export interface Ending {
  end     : number
  reached : boolean
}

/**
 * One file of a run's directory as the run stands, what it holds and whether
 * it is there yet.
 */
export interface Listed {
  state : string
  there : boolean
}

/**
 * The run's length and the interval at which it writes a checkpoint and plays
 * an evaluation, as the settings declare them, beside the directory it writes
 * into and the steps one beat of the widget moves it.
 */
export const RUN = {
  beat       : 20_000,
  checkpoint : SETTINGS.checkpoint_steps,
  directory  : 'data/runs/20261024T061530.482913Z',
  evaluation : SETTINGS.evaluation_steps,
  steps      : SETTINGS.steps
} as const

/**
 * Each file a run writes into its directory, by the name the package gives it,
 * beside when the run writes it.
 */
export const FILES = [
  { name: 'run.json', when: 'as the run starts' },
  { name: 'episodes.jsonl', when: 'a line per episode' },
  { name: 'checkpoint.npz', when: `each ${count(RUN.checkpoint)} steps, at the end` },
  { name: 'evaluations.jsonl', when: `a line each ${count(RUN.evaluation)} steps` },
  { name: 'baseline.json', when: 'at the first evaluation' },
  { name: 'stop', when: 'by squirtl stop' }
] as const

/**
 * The made-up run's episodes, each running to the step limit until the agent
 * has trained past a third of the run, and most reaching the starter within a
 * few hundred steps after it.
 */
export const ENDINGS: readonly Ending[] = (() => {
  const random = seeded(17)
  const limit  = SETTINGS.environment.max_episode_steps
  const ends   = [] as Ending[]

  for (let step = 0; step < RUN.steps;) {
    const length = step > RUN.steps / 3 && random() < 0.8 ? 120 + Math.floor(random() * 900) : limit
    step = Math.min(RUN.steps, step + length)
    ends.push({ end: step, reached: length < limit })
  }
  return ends
})()

/**
 * Lists the step of the first episode end reaching each multiple of `every`,
 * where the run writes a checkpoint or plays an evaluation.
 */
export function dueAt(every: number): number[] {
  return ENDINGS.map(each => each.end).filter((end, n, ends) =>
    Math.floor(end / every) > Math.floor((ends[n - 1] ?? 0) / every))
}

/**
 * Counts `n` lines of a file a run writes a line to.
 */
const lines = (n: number): string => counted(n, 'line')

/**
 * The made-up run at one step: the episodes it has finished, the files it has
 * written, and whether `squirtl stop` has written the stop file, after which
 * the run ends when its episode does.
 */
export class Training {
  ended  = false
  step   = 0
  stopAt = null as number | null

  /**
   * The count of episodes the run has finished.
   */
  get finished(): number {
    return ENDINGS.filter(each => each.end <= this.step).length
  }

  /**
   * Whether the stop file is written and the run has not reached its
   * episode's end.
   */
  get stopping(): boolean {
    return this.stopAt !== null && !this.ended
  }

  /**
   * Moves the run one beat, or to its episode's end once the stop file is
   * written.
   */
  advance() {
    if (this.stopAt !== null) {
      this.step  = ENDINGS.find(each => each.end > this.stopAt!)?.end ?? RUN.steps
      this.ended = true
      return
    }
    this.step  = Math.min(RUN.steps, this.step + RUN.beat)
    this.ended = this.step >= RUN.steps
  }

  /**
   * Lists what each of `FILES` holds as the run stands.
   */
  files(): Listed[] {
    const checkpoints = dueAt(RUN.checkpoint).filter(end => end <= this.step)
    const evaluations = dueAt(RUN.evaluation).filter(end => end <= this.step).length
    const checkpoint  = this.ended ? `At the end, step ${count(this.step)}`
                      : checkpoints.length > 0 ? `Last at step ${count(checkpoints.at(-1)!)}` : 'Not yet'

    return [
      { state: 'Written', there: true },
      { state: this.finished > 0 ? lines(this.finished) : 'No line yet', there: this.finished > 0 },
      { state: checkpoint, there: this.ended || checkpoints.length > 0 },
      { state: evaluations > 0 ? lines(evaluations) : 'No line yet', there: evaluations > 0 },
      { state: evaluations > 0 ? 'Written' : 'Not yet', there: evaluations > 0 },
      { state: this.stopAt === null ? 'Not there' : 'Written', there: this.stopAt !== null }
    ]
  }

  /**
   * Starts the run over from its first step.
   */
  reset() {
    this.ended  = false
    this.step   = 0
    this.stopAt = null
  }

  /**
   * Spells where the run stands, the step and the episode it is playing, the
   * episode it ends with once the stop file is written, or how it ended.
   */
  status(): string {
    const { finished } = this

    if (this.ended) {
      return this.stopAt === null
        ? `Ended at step ${count(RUN.steps)} after ${count(finished)} episodes, with a checkpoint`
        : `Stopped at the end of episode ${count(finished)}, step ${count(this.step)}, with a checkpoint`
    }
    return this.stopAt === null
      ? `Step ${count(this.step)} of ${count(RUN.steps)}, episode ${count(finished + 1)}`
      : `The stop file is written, so the run ends when episode ${count(finished + 1)} does`
  }

  /**
   * Writes the stop file, as `squirtl stop` does, unless the run has ended or
   * the file is already there.
   */
  stop() {
    if (!this.ended && this.stopAt === null) this.stopAt = this.step
  }
}
