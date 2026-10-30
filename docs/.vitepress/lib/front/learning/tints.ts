import * as identity from '../../identity/identity.ts'

/**
 * Mixes the hexes `a` and `b` channel by channel, `t` of the way from `a` to
 * `b`.
 */
function mix(a: string, b: string, t: number): string {
  const channels = identity.mixRgb(identity.rgbOf(a), identity.rgbOf(b), t)
  return `#${channels.map(channel => channel.toString(16).padStart(2, '0')).join('')}`
}

/**
 * Mixes the crossfade of every stack of walks, a stack named by the bits of the
 * walks it holds, each of its `steps` steps the sprite's shades that far around
 * from one walk's colors through the next and back to the first.
 *
 * Returns:
 *   The steps of each stack, each the fills of the sprite's shades, empty for
 *   the stack holding no walk.
 */
export function blendsOf(fills: readonly (readonly string[])[], steps: number): string[][][] {
  return Array.from({ length: 2 ** fills.length }, (_, stack) => {
    const members = fills.filter((__, n) => stack & (1 << n))
    if (members.length === 0) return []
    return Array.from({ length: steps }, (__, step) => {
      const at   = step / steps * members.length
      const from = Math.floor(at)
      const to   = members[(from + 1) % members.length]!
      return members[from]!.map((fill, shade) => mix(fill, to[shade]!, at - from))
    })
  })
}

/**
 * Reads the fills a sprite in `hue` takes, from the lightest of the Game Boy's
 * shades to the darkest: the screen's white, the hue's pale step, the hue
 * itself, and its deep step.
 */
export function fillsOf(hue: identity.Hue): string[] {
  const { light } = identity.IDENTITY.hues[hue]
  return [identity.hexOf('ground'), light.pale, identity.hueHex(hue), light.deep]
}

/**
 * Chooses the hue of each of `walks` walks read in order of training, the
 * latest in the agent's hue and each earlier one in the hue after its
 * successor's in the identity's order, wrapping from its end to its start.
 */
export function walkHuesOf(walks: number): identity.Hue[] {
  const order  = identity.IDENTITY.order as identity.Hue[]
  const latest = order.indexOf(identity.roleHue('agent'))
  return Array.from({ length: walks }, (_, n) => order[(latest + walks - 1 - n) % order.length]!)
}
