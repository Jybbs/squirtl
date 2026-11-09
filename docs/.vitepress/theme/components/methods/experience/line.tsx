import * as experience from '../../../../lib/methods/experience.ts'
import { count }       from '../../../../lib/widgets/numbers.ts'
import { ROLES }       from '../../kit/hues.ts'
import { LABEL }       from '../../kit/widget.ts'

/**
 * Draws the line of time: a grid line at each tick, the lane along its foot,
 * the update's dot at its right end, and an arc from the update to each step it
 * reads, landing `ages` steps ago.
 */
export function drawLine(ages: readonly number[], label: string) {
  const { height, lane, left, right, top, width } = experience.LINE

  return (
    <svg aria-label={label} class="block h-auto w-full overflow-visible" role="img" viewBox={`0 0 ${width} ${height}`}>
      {experience.TICKS.map(age => (
        <line class="stroke-rule" stroke-width="1" x1={experience.xOf(age)} x2={experience.xOf(age)} y1={lane - 6} y2={lane + 16} />
      ))}
      <rect class={ROLES.agent.fill} height="10" opacity="0.3" rx="2" width={right - left} x={left} y={lane} />
      <circle class={ROLES.agent.fill} cx={right} cy={top} r="6" />
      <g class={['fill-none', ROLES.agent.stroke]} opacity="0.6" stroke-width="1.2">
        {ages.map(age => <path d={experience.arcOf(age)} />)}
      </g>
    </svg>
  )
}

/**
 * Draws the name under each of the line's ticks, the steps ago it marks or now
 * at the update, on a line a zero-width space holds open at the label's
 * height.
 */
export function drawTicks() {
  return (
    <p aria-hidden="true" class={[LABEL, 'experience-ticks relative m-0']}>
      {'\u200B'}
      {experience.TICKS.map(age => (
        <span class={[LABEL, 'experience-tick absolute top-0 whitespace-nowrap']} style={{ left: `${(experience.xOf(age) / experience.LINE.width * 100).toFixed(2)}%` }}>
          {age ? `${count(age)} ago` : 'now'}
        </span>
      ))}
    </p>
  )
}
