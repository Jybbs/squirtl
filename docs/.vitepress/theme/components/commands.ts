import { CommandsFetch }    from './commands/fetch.tsx'
import { CommandsPack }     from './commands/pack.tsx'
import { CommandsTerminal } from './commands/terminal.tsx'
import { CommandsWatch }    from './commands/watch.tsx'

/**
 * The widgets a page of the Commands section closes a part on.
 */
export const COMMANDS = [CommandsFetch, CommandsPack, CommandsTerminal, CommandsWatch] as const
