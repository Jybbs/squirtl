import * as experience  from '../../../../lib/methods/experience.ts'
import type { Windows } from '../../../../lib/methods/experience/windows.ts'

/**
 * Draws the strip of windows beneath the line, each at the step its arc lands
 * on.
 */
export function drawStrip({ canvases, shown }: Windows) {
  return (
    <div aria-hidden="true" class="experience-strip relative mt-2">
      {shown.map((each, n) => {
        const { left, top } = experience.windowAt(each.value.age, n)
        return (
          <canvas
            class="experience-window pixelated absolute aspect-square rounded-1 motion-safe:transition-[left,top] motion-safe:ease-glide"
            height={experience.WINDOW}
            ref={(canvas: unknown) => { if (canvas) canvases.value[n] = canvas as HTMLCanvasElement }}
            style={{ left: `${(left * 100).toFixed(2)}%`, top: `${top * 100}%` }}
            width={experience.WINDOW}
          />
        )
      })}
    </div>
  )
}
