import * as drawings from '../../../../lib/marks/drawings.ts'
import * as logo     from '../../../../lib/marks/logo.ts'

/**
 * The fill class of each color a dot of the mark takes.
 */
const FILLS: Readonly<Record<logo.Tone, string>> = {
  'ahead'   : 'fill-ahead',
  'ink'     : 'fill-ink',
  'trail-1' : 'fill-trail-1',
  'trail-2' : 'fill-trail-2',
  'trail-3' : 'fill-trail-3'
}

/**
 * Draws the character of `mark` at `index` as a group of its own: its dots,
 * then Blue's block where he walks the letter, his walking frame showing until
 * the drawing marks him standing, then the Poké Ball after the dots of the
 * letter it ends.
 */
function drawLetter(mark: logo.Mark, index: number) {
  const dots   = mark.dots.filter(dot => dot.index === index)
  const letter = dots[0]!.letter
  const block  = mark.blocks.find(each => each.letter === letter)

  return (
    <g
      class="origin-top-left transform-view"
      data-ink={block ? undefined : ''}
      data-letter={index}
      data-walk={block?.letter}
    >
      {dots.map(dot => (
        <circle
          class={FILLS[logo.toneOf(dot)]}
          cx={dot.x}
          cy={dot.y}
          data-ahead={dot.kind === 'ahead' ? '' : undefined}
          data-step={dot.kind === 'trail' ? dot.step : undefined}
          r={logo.dotRadius}
        />
      ))}
      {block && [
        <rect
          class="fill-block"
          height={block.side}
          rx={block.radius}
          width={block.side}
          x={block.x}
          y={block.y}
        />,
        <g class="group-data-standing:hidden" innerHTML={drawings.poseOf(block, block.frame)} />,
        <g class="hidden group-data-standing:inline" innerHTML={drawings.poseOf(block, block.stand)} />
      ]}
      {mark.ball.index === index && <g data-ball innerHTML={drawings.ballOf(mark)} />}
    </g>
  )
}

/**
 * Draws `mark` as an SVG viewed through its frame, one group per character,
 * with Blue standing between steps where `standing` is set.
 */
export function drawMark(mark: logo.Mark, standing = false) {
  return (
    <svg
      class="group block h-auto w-full overflow-visible"
      data-standing={standing ? '' : undefined}
      viewBox={drawings.viewBoxOf(mark.view)}
    >
      {mark.lefts.map((_, index) => drawLetter(mark, index))}
    </svg>
  )
}
