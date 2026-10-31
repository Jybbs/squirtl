import type { Hue, Role } from '../../../lib/identity/identity.ts'

/**
 * The classes drawing a part in one hue: its badge's middle step as a
 * ground, its mark as a fill, its lightest shade as a ground, its mark as the
 * color an inline mark inks in, its third shade as a ring, its mark as a rule,
 * and its text step.
 */
interface HueClasses {
  badge  : string
  fill   : string
  ground : string
  ink    : string
  ring   : string
  rule   : string
  text   : string
}

/**
 * The classes filling and stroking a part in the hue of a role.
 */
interface RoleClasses {
  fill   : string
  stroke : string
}

/**
 * The classes drawing each hue, a series hue's or a section's, each written
 * whole so the theme's scan finds it.
 */
export const HUES: Readonly<Record<Hue, HueClasses>> = {
  amethyst: {
    badge  : 'bg-amethyst-badge-2',
    fill   : 'fill-amethyst-mark',
    ground : 'bg-amethyst-1',
    ink    : 'text-amethyst-mark',
    ring   : 'border-amethyst-3',
    rule   : 'border-amethyst-mark',
    text   : 'text-amethyst-text'
  },

  cerulean: {
    badge  : 'bg-cerulean-badge-2',
    fill   : 'fill-cerulean-mark',
    ground : 'bg-cerulean-1',
    ink    : 'text-cerulean-mark',
    ring   : 'border-cerulean-3',
    rule   : 'border-cerulean-mark',
    text   : 'text-cerulean-text'
  },

  denim: {
    badge  : 'bg-denim-badge-2',
    fill   : 'fill-denim-mark',
    ground : 'bg-denim-1',
    ink    : 'text-denim-mark',
    ring   : 'border-denim-3',
    rule   : 'border-denim-mark',
    text   : 'text-denim-text'
  },

  fern: {
    badge  : 'bg-fern-badge-2',
    fill   : 'fill-fern-mark',
    ground : 'bg-fern-1',
    ink    : 'text-fern-mark',
    ring   : 'border-fern-3',
    rule   : 'border-fern-mark',
    text   : 'text-fern-text'
  },

  forest: {
    badge  : 'bg-forest-badge-2',
    fill   : 'fill-forest-mark',
    ground : 'bg-forest-1',
    ink    : 'text-forest-mark',
    ring   : 'border-forest-3',
    rule   : 'border-forest-mark',
    text   : 'text-forest-text'
  },

  heath: {
    badge  : 'bg-heath-badge-2',
    fill   : 'fill-heath-mark',
    ground : 'bg-heath-1',
    ink    : 'text-heath-mark',
    ring   : 'border-heath-3',
    rule   : 'border-heath-mark',
    text   : 'text-heath-text'
  },

  indigo: {
    badge  : 'bg-indigo-badge-2',
    fill   : 'fill-indigo-mark',
    ground : 'bg-indigo-1',
    ink    : 'text-indigo-mark',
    ring   : 'border-indigo-3',
    rule   : 'border-indigo-mark',
    text   : 'text-indigo-text'
  },

  seacaller: {
    badge  : 'bg-seacaller-badge-2',
    fill   : 'fill-seacaller-mark',
    ground : 'bg-seacaller-1',
    ink    : 'text-seacaller-mark',
    ring   : 'border-seacaller-3',
    rule   : 'border-seacaller-mark',
    text   : 'text-seacaller-text'
  }
}

/**
 * The classes filling and stroking each role's hue, each written whole so the
 * theme's scan finds it.
 */
export const ROLES: Readonly<Record<Role, RoleClasses>> = {
  agent     : { fill: 'fill-agent', stroke: 'stroke-agent' },
  milestone : { fill: 'fill-milestone', stroke: 'stroke-milestone' },
  novelty   : { fill: 'fill-novelty', stroke: 'stroke-novelty' },
  random    : { fill: 'fill-random', stroke: 'stroke-random' },
  starter   : { fill: 'fill-starter', stroke: 'stroke-starter' }
}
