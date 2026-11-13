import { IdentityFaces }   from './identity/faces.tsx'
import { IdentityLogo }    from './identity/logo.tsx'
import { IdentityOrder }   from './identity/order.tsx'
import { IdentityPalette } from './identity/palette.tsx'
import { IdentityResults } from './identity/results.tsx'
import { IdentityTagline } from './identity/tagline.tsx'

/**
 * The widgets the Identity page closes a part on.
 */
export const IDENTITY = [IdentityFaces, IdentityLogo, IdentityOrder, IdentityPalette, IdentityResults, IdentityTagline] as const
