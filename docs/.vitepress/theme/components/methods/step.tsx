import { defineComponent, onMounted, ref } from 'vue'

import { Episode }            from '../../../lib/game/episode.ts'
import { RoomImages }         from '../../../lib/game/images.ts'
import { padMark, pressName } from '../../../lib/game/pad.ts'
import { GameScreen, SCREEN } from '../../../lib/game/screen.ts'
import * as step              from '../../../lib/methods/step.ts'
import { useStepPlayback }    from '../../../lib/methods/step/playback.ts'
import { Chip }               from '../kit/chip.tsx'
import { ROLES }              from '../kit/hues.ts'
import { COVER, DETAIL }      from '../kit/widget.ts'

/**
 * The marks the sheet's key names, drawn as the sheet draws them: the bar over
 * the frames a press holds, the dot on the frame the game reads the pad on, a
 * frame run but never drawn, and the ring round the frame PyBoy draws.
 */
const MARKS = {
  bar   : '<svg viewBox="0 0 16 16"><rect x="1" y="6" width="14" height="4" fill="currentColor"/></svg>',
  dot   : '<svg viewBox="0 0 16 16"><rect x="6" y="6" width="4" height="4" fill="currentColor"/></svg>',
  drawn : '<svg viewBox="0 0 16 16"><rect x="2" y="2" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
  run   : '<svg viewBox="0 0 16 16"><rect x="2.5" y="2.5" width="11" height="11" fill="currentColor" opacity="0.4"/></svg>'
}

/**
 * The sheet's key, each entry its mark, its one-word name, and the frames it
 * covers as a unit beside a figure.
 */
const KEY = [
  { mark: MARKS.bar, name: 'Held', note: 'frames', role: 'agent', value: `1–${step.HOLD}` },
  { mark: MARKS.dot, name: 'Read', note: 'frame', role: 'none', value: '1 or 2' },
  { mark: MARKS.run, name: 'Not drawn', note: 'frames', role: 'none', value: `1–${step.FRAMES - 1}` },
  { mark: MARKS.drawn, name: 'Returned', note: 'frame', role: 'agent', value: String(step.FRAMES) }
] as const

/**
 * The words the widget sets, the name a screen reader reads for the sheet and
 * for its slider.
 */
const WORDS = {
  sheet  : 'The frames of ten steps, a row a step and a column a frame, the seventeenth of each row the one PyBoy draws',
  slider : 'The frame the sheet stands at, a row a step and a column a frame'
}

/**
 * The pixels from one cell's corner to the next, and the sheet's width and
 * height.
 */
const PITCH  = step.SHEET.cell + step.SHEET.gap
const WIDTH  = step.FRAMES * PITCH
const HEIGHT = step.STEPS.length * PITCH

/**
 * Draws every frame of every step into `canvas`, each cell the part of the
 * bedroom's screen round Blue as pret/pokered draws it on that frame, leaving
 * the canvas blank where it gives no 2D context.
 */
function paintSheet(canvas: HTMLCanvasElement, images: RoomImages): void {
  const episode = new Episode()
  const screen  = new GameScreen(episode, images)
  const source  = Object.assign(document.createElement('canvas'), SCREEN).getContext('2d')
  const context = canvas.getContext('2d')
  const { cell, crop, gap } = step.SHEET
  if (!source || !context) return
  episode.at                    = step.START.at
  context.imageSmoothingEnabled = false
  step.STEPS.forEach((each, s) => each.frames.forEach((frame, f) => {
    screen.view.at.splice(0, 2, ...step.viewAt(each, f + 1))
    episode.facing = frame.facing
    screen.stance  = frame.stance
    screen.draw(source)
    context.drawImage(source.canvas, crop[0], crop[1], cell, cell, f * PITCH + gap / 2, s * PITCH + gap / 2, cell, cell)
  }))
}

/**
 * Draws the marks over the sheet standing at `at`: a veil over each frame
 * fading it to its strength, the bar over the frames each press holds, the dot
 * on the frame the game reads the pad on, the ring round each frame PyBoy draws
 * once the position has passed it, and the square drawn round the frame it
 * stands on.
 */
function drawMarks(at: number) {
  const { cell, gap } = step.SHEET
  const now           = step.cellOf(at)
  const fade          = 'motion-safe:transition-opacity'
  return (
    <svg aria-hidden="true" class="absolute inset-0 block size-full" viewBox={`0 0 ${WIDTH} ${HEIGHT}`}>
      {step.STEPS.map((each, s) => {
        const y = s * PITCH + gap / 2
        return [
          ...each.frames.map((_, f) => (
            <rect
              class={['fill-ground', fade]}
              height={cell}
              style={{ opacity: 1 - step.strengthOf(at, s * step.FRAMES + f) }}
              width={cell}
              x={f * PITCH + gap / 2}
              y={y}
            />
          )),
          <rect
            class={['fill-none', ROLES.agent.stroke, fade]}
            height={cell - 2}
            stroke-width="2"
            style={{ opacity: s * step.FRAMES + step.FRAMES - 1 <= at ? 1 : 0 }}
            width={cell - 2}
            x={(step.FRAMES - 1) * PITCH + gap / 2 + 1}
            y={y + 1}
          />,
          each.press === null ? null : <rect class={ROLES.agent.fill} height="3" width={step.HOLD * PITCH - gap} x={gap / 2} y={y} />,
          <rect class="fill-ink" height="3" width="3" x={(each.read - 1) * PITCH + gap / 2 + cell - 5} y={y + cell - 5} />
        ]
      })}
      {now.f === step.FRAMES ? null : (
        <rect
          class="fill-none stroke-ink"
          height={cell - 1}
          stroke-width="1"
          width={cell - 1}
          x={(now.f - 1) * PITCH + gap / 2 + 0.5}
          y={now.s * PITCH + gap / 2 + 0.5}
        />
      )}
    </svg>
  )
}

/**
 * Draws the frame numbers over the sheet's columns, the last, which PyBoy
 * draws, in the agent's Denim.
 */
function drawHead() {
  return (
    <div aria-hidden="true" class="step-head grid" style={{ gridTemplateColumns: `repeat(${step.FRAMES}, minmax(0, 1fr))` }}>
      {Array.from({ length: step.FRAMES }, (_, f) => (
        <span class={[DETAIL, 'step-number text-center', f + 1 === step.FRAMES ? 'font-bold text-denim-text' : '']}>{f + 1}</span>
      ))}
    </div>
  )
}

/**
 * Draws the press each row of the sheet holds as the Game Boy's pad, beside
 * its name for a screen reader.
 */
function drawLabels() {
  return (
    <div class="step-labels grid" style={{ gridTemplateRows: `repeat(${step.STEPS.length}, minmax(0, 1fr))` }}>
      {step.STEPS.map(each => (
        <span class="grid min-h-0 place-items-center text-denim-mark" title={pressName(each.press)}>
          <span aria-hidden="true" class="step-pad grid aspect-square place-items-center rounded-full bg-athens-gray" innerHTML={padMark(each.press)} />
          <span class="visually-hidden">{pressName(each.press)}</span>
        </span>
      ))}
    </div>
  )
}

/**
 * One step of the environment as a sheet of ten steps by seventeen frames, the
 * press held over the first two of each row, a dot where the game reads the
 * pad, every frame the game runs drawn faint, and the seventeenth, the one
 * PyBoy draws and the step returns, at full strength in the agent's Denim. The
 * sheet plays frame by frame, and a press or a drag on a frame or the arrow
 * keys hold it there.
 */
export const MethodsStep = defineComponent({
  name  : 'MethodsStep',
  setup : () => {
    const box    = ref<HTMLElement>()
    const canvas = ref<HTMLCanvasElement>()
    const thumb  = ref<HTMLElement>()
    const { at, band, scrub, where } = useStepPlayback(box, thumb, WORDS.slider)

    onMounted(() => {
      const images = new RoomImages()
      images.whenReady(() => paintSheet(canvas.value!, images), ['bedroom'])
    })

    return () => (
      <div class="@container grid gap-4">
        <div class="step-sheet grid gap-x-2 gap-y-1">
          {drawHead()}
          {drawLabels()}
          <div {...scrub.root.value} class="step-cells relative" ref={box}>
            <canvas aria-label={WORDS.sheet} class="pixelated block h-auto w-full" height={HEIGHT} ref={canvas} role="img" width={WIDTH} />
            {drawMarks(at.value)}
            <div {...band.control.value} class={COVER.control} onPointerdown={band.press} onPointermove={(event: PointerEvent) => { if (event.buttons) band.point(event) }} />
            <div {...scrub.thumb.value} class={COVER.thumb} ref={thumb} />
          </div>
        </div>
        <div class="grid gap-3">
          <span class={[DETAIL, 'step-status text-ink']}>{`Step ${where.value.s + 1} of ${step.STEPS.length} · frame ${where.value.f} of ${step.FRAMES}`}</span>
          <div class="step-key grid grid-cols-1 gap-2 @lg:grid-cols-2">
            {KEY.map(each => <Chip class="w-full" {...each} />)}
          </div>
        </div>
      </div>
    )
  }
})
