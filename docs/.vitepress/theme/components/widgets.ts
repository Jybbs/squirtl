import { COMMANDS } from './commands.ts'
import { FRONT }    from './front.ts'
import { IDENTITY } from './identity.ts'
import { METHODS }  from './methods.ts'
import { RESULTS }  from './results.ts'

/**
 * Every widget the theme registers by its name, the front page's story, each
 * one a section's page closes a part on, and each the Identity page closes a
 * part on.
 */
export const COMPONENTS = [...COMMANDS, ...METHODS, ...RESULTS, ...FRONT, ...IDENTITY] as const
