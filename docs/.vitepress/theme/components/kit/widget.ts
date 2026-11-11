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
 * The classes of a list a widget lays out itself, clearing the indent, the
 * marker, and the gap between items the default theme gives a page's lists.
 */
export const LIST = 'm-0 list-none p-0 *:mt-0'

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
 * The classes of a slider's parts laid over the whole of the drawing it
 * scrubs, the control taking no text selection as a pointer drags across it.
 */
export const COVER = {
  control : [SCRUB_PARTS.control, 'absolute inset-0 select-none'],
  thumb   : [SCRUB_PARTS.thumb, 'absolute inset-0']
}

/**
 * The classes of a swatch, a rounded square in the current color, which a chip
 * or an entry of a key shows where it carries no mark.
 */
export const SWATCH = 'size-swatch rounded-swatch bg-current'
