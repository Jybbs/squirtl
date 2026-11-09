import { describe, expect, it } from 'vitest'

import * as terminal from '../../../lib/commands/terminal.ts'

/**
 * Plays a fresh run `beats` beats.
 */
function played(beats: number): terminal.Training {
  const run = new terminal.Training()
  for (let beat = 0; beat < beats; beat++) run.advance()
  return run
}

describe('ENDINGS', () => {
  it('runs each episode to the step limit until a third of the run has passed, then mostly reaches the starter', () => {
    const early = terminal.ENDINGS.filter(each => each.end <= terminal.RUN.steps / 3)

    expect([early.every(each => !each.reached), terminal.ENDINGS.some(each => each.reached)]).toStrictEqual([true, true])
  })

  it('ends its last episode at the run’s last step', () => {
    expect(terminal.ENDINGS.at(-1)!.end).toBe(terminal.RUN.steps)
  })
})

describe('dueAt', () => {
  it('takes the first episode end at or past each multiple of the interval', () => {
    const due = terminal.dueAt(terminal.RUN.checkpoint)

    expect(due.map(end => Math.floor(end / terminal.RUN.checkpoint))).toStrictEqual(
      Array.from({ length: due.length }, (_, n) => n + 1))
  })
})

describe('Training', () => {
  it('starts with only its record written', () => {
    expect([new terminal.Training().files().map(file => file.there), new terminal.Training().status()]).toStrictEqual([
      [true, false, false, false, false, false],
      'Step 0 of 2,500,000, episode 1'
    ])
  })

  it('writes its checkpoints, its evaluations, and the baseline as it trains', () => {
    expect(played(20).files()).toStrictEqual([
      { state: 'Written', there: true },
      { state: '39 lines', there: true },
      { state: 'Last at step 256,000', there: true },
      { state: '1 line', there: true },
      { state: 'Written', there: true },
      { state: 'Not there', there: false }
    ])
  })

  it('ends at its last step with a checkpoint once it has trained in full', () => {
    const run = played(200)

    expect([run.ended, run.status(), run.files()[2]!.state]).toStrictEqual([
      true, `Ended at step 2,500,000 after ${terminal.ENDINGS.length} episodes, with a checkpoint`, 'At the end, step 2,500,000'
    ])
  })

})

describe('Training once the stop file is written', () => {
  it('ends at its episode’s end once the stop file is written, and writes it only once', () => {
    const run = played(3)

    run.stop()
    expect(run.status()).toBe('The stop file is written, so the run ends when episode 6 does')
    run.stop()
    run.advance()
    expect([run.stopAt, run.status(), run.files()[5]]).toStrictEqual([
      60000, 'Stopped at the end of episode 6, step 61,440, with a checkpoint', { state: 'Written', there: true }
    ])
  })

  it('writes no stop file once it has ended, and starts over on a reset', () => {
    const run = played(200)

    run.stop()
    expect(run.stopAt).toBeNull()
    run.reset()
    expect([run.step, run.ended]).toStrictEqual([0, false])
  })

  it('ends at the run’s last step where the stop file lands in its last episode', () => {
    const run = new terminal.Training()

    run.step = terminal.RUN.steps - 1
    run.stop()
    run.advance()
    expect(run.step).toBe(terminal.RUN.steps)
  })
})
