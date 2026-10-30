/**
 * The classes of a quiet line of detail set beneath a label, such as a step or
 * the size of an entry.
 */
export const DETAIL = 'font-code text-small leading-snug text-quiet tabular-nums'

/**
 * The classes of a canvas showing the game's world, which scale it to its
 * column and edge it in the rule with its pixels drawn square.
 */
export const GAME_VIEW = 'pixelated block h-auto w-full rounded-2 border-hairline border-rule'

/**
 * The classes of a label in capitals, over a key, over a figure, or over a
 * caption.
 */
export const LABEL = 'font-code text-label leading-snug font-medium tracking-caps text-quiet uppercase'

/**
 * The classes of the parts of a drawing that serves as its own slider, its
 * control showing the cursor that drags it while a touch still scrolls the
 * page, and its thumb ringed while it has focus and passing a pointer's press
 * through to the drawing.
 */
export const SCRUB_PARTS = {
  control : 'cursor-ew-resize touch-pan-y',
  thumb   : 'focus-ring pointer-events-none'
}

/**
 * The classes of a swatch, a rounded square in the current color, which a chip
 * or an entry of a key shows where it carries no mark.
 */
export const SWATCH = 'size-swatch rounded-swatch bg-current'
