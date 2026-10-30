import { describe, expect, it } from 'vitest'

import { badgeMarkup } from '../../../lib/drawing/badges.ts'
import { runsOf }      from '../../../lib/drawing/sprites.ts'
import { IDENTITY }    from '../../../lib/identity/identity.ts'

describe('badgeMarkup', () => {
  it('crops the Boulder Badge to the fourteen pixels square it draws in', () => {
    expect(badgeMarkup(IDENTITY.badges[0]!, 'fern'))
      .toMatch(/^<svg viewBox="1 1 14 14" shape-rendering="crispEdges" aria-hidden="true">/u)
  })

  it('centers a badge narrower than it is tall in a square as tall as it', () => {
    const grid  = ['0000', '0110', '0110', '0110']
    const badge = { grid, name: 'Narrow' }

    expect(badgeMarkup(badge, 'heath')).toContain('viewBox="0.5 1 3 3"')
  })

  it('draws each run in the badge shade its hue gives, one rectangle a run', () => {
    const badge = IDENTITY.badges[1]!
    const fills = Array.from(badgeMarkup(badge, 'denim').matchAll(/fill="([^"]+)"/gu), ([, fill]) => fill)

    expect(fills).toStrictEqual(runsOf(badge.grid).map(run => `var(--color-denim-badge-${run.shade})`))
  })
})
