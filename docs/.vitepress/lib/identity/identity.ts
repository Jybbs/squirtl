import IDENTITY from '../rendered/identity.json' with { type: 'json' }

/**
 * One of the gym badges a section carries as its mark.
 */
export type Badge = Identity['badges'][number]

/**
 * The folder a section of the site opens on, under which the identity gives
 * the section its hue.
 */
export type Folder = keyof Identity['sections']

/**
 * A hue's name, a series hue's or a section's.
 */
export type Hue = keyof Identity['hues']

/**
 * The site's visual identity, as `squirtl write docs` writes it from the
 * package's declaration.
 */
export type Identity = typeof IDENTITY

/**
 * A role a drawing gives one hue wherever it draws it.
 */
export type Role = keyof Identity['roles']

/**
 * A color scheme the site switches between.
 */
export type Scheme = keyof Identity['schemes']

/**
 * A color the identity names, among the palette's tokens, the neutrals, and
 * Denim's ramp.
 */
export type Token = keyof Identity['colors'] | keyof Identity['neutrals'] | keyof Identity['ramp']

export { IDENTITY }

/**
 * Every color the identity names, the palette's tokens, the neutrals, and
 * Denim's ramp in one table keyed by token.
 */
const swatches: Readonly<Record<Token, { hex: string }>> = {
  ...IDENTITY.colors,
  ...IDENTITY.neutrals,
  ...IDENTITY.ramp
}

/**
 * The hex of each of the Game Boy's four shades a sprite takes, from the
 * lightest to the darkest, as the identity maps them.
 */
export const spriteShades: readonly string[] = IDENTITY.logo.shades.map(token => hexOf(token as Token))

/**
 * Reads the hex the identity gives the color `token` names, whichever of its
 * tables declares it.
 */
export function hexOf(token: Token): string {
  return swatches[token].hex
}

/**
 * Reads the hex of the hue `hue` itself.
 */
export function hueHex(hue: Hue): string {
  return hexOf(IDENTITY.hues[hue].token as Token)
}

/**
 * Mixes the colors `from` and `to` channel by channel, `t` of the way from
 * `from` to `to`, rounding each channel to a whole byte.
 */
export function mixRgb(from: readonly number[], to: readonly number[], t: number): number[] {
  return from.map((each, channel) => Math.round(each + (to[channel]! - each) * t))
}

/**
 * Reads the red, green, and blue bytes a hex such as `#3d6fd0` names.
 */
export function rgbOf(hex: string): number[] {
  const value = Number.parseInt(hex.slice(1), 16)
  return [value >> 16, (value >> 8) & 255, value & 255]
}

/**
 * Reads the series hue the identity gives the role `role`.
 */
export function roleHue(role: Role): Hue {
  return IDENTITY.roles[role] as Hue
}

/**
 * Reads the hue the identity gives the section opening on `folder`.
 */
export function sectionHue(folder: Folder): Hue {
  return IDENTITY.sections[folder] as Hue
}
