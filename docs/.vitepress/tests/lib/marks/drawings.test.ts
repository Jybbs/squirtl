import { describe, expect, it } from 'vitest'

import { spriteMarkup }            from '../../../lib/drawing/sprites.ts'
import { IDENTITY, spriteShades } from '../../../lib/identity/identity.ts'
import * as drawings              from '../../../lib/marks/drawings.ts'
import { markOf }                 from '../../../lib/marks/logo.ts'

describe('drawings', () => {
  it.each(['dark', 'light'] as const)('draws the %s icon as the R and the L with crisp edges', scheme => {
    const svg = drawings.drawIcon(scheme)
    expect(svg).toMatch(/^<svg xmlns="http:\/\/www\.w3\.org\/2000\/svg" viewBox="-10 90 1020 620" role="img" /u)
    expect(svg).toContain('shape-rendering="crispEdges"')
    expect(svg.match(/<circle /gu)).toHaveLength(markOf('RL').dots.length)
  })

  it.each([
    ['dark', '#7097df'],
    ['light', '#3d6fd0']
  ] as const)('draws the %s logo with its blocks in %s', (scheme, hex) => {
    const svg = drawings.drawLogo(scheme)
    expect(svg).toContain('viewBox="-10 -10 3720 820"')
    expect(svg).not.toContain('crispEdges')
    expect(svg.match(new RegExp(`<rect [^>]* rx="60" fill="${hex}"/>`, 'gu'))).toHaveLength(2)
  })

  it('draws the icon’s Poké Ball and each Blue standing in his walking frame', () => {
    const mark  = markOf('RL')
    const svg   = drawings.drawIcon('light')
    const poses = mark.blocks.map(block => drawings.poseOf(block, block.frame))
    expect(svg).toContain(drawings.ballOf(mark))
    expect(poses.filter(pose => svg.includes(pose))).toHaveLength(2)
  })

  it('draws the favicon as the light icon on an Athens Gray tile', () => {
    const svg = drawings.drawFavicon()
    expect(svg).toContain('viewBox="0 0 100 100"')
    expect(svg).toContain('<rect width="100" height="100" rx="18" fill="#f3f4f7"/>')
    expect(svg).toContain('<svg x="8" y="25" width="84" height="51.1" viewBox="-10 90 1020 620">')
    expect(svg).toContain(drawings.drawIcon('light')
      .replace(/^<svg[^>]*>/u, '')
      .replace(/<\/svg>$/u, ''))
  })

  it('draws Blue standing in his block, in the theme’s block color with the logo’s corners', () => {
    const svg  = drawings.drawBlock()
    const pose = spriteMarkup(IDENTITY.sprites.player.frames[0]!, {
      fills : spriteShades,
      size  : 11.5,
      x     : 18,
      y     : 18
    })
    expect(svg).toContain('viewBox="0 0 220 220"')
    expect(svg).toContain('<rect width="220" height="220" rx="60" fill="var(--color-block)"/>')
    expect(svg).toContain(pose)
  })
})
