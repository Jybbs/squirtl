import { COMMANDS } from './commands.ts'
import { FRONT }    from './front.ts'
import { METHODS }  from './methods.ts'
import { RESULTS }  from './results.ts'

/**
 * Every widget the theme registers by its name, the front page's story and
 * each one a section's page closes a part on.
 */
export const COMPONENTS = [...COMMANDS, ...METHODS, ...RESULTS, ...FRONT] as const
