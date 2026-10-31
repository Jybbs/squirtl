import { expect } from 'vitest'

/**
 * The marks and words the project's writing rules keep out of every sentence
 * the site publishes, each beside the rule it breaks.
 */
const BREAKS = [
  [/—/u, 'an em-dash'],
  [/[a-z]; [a-z]/u, 'a semicolon joining two clauses'],
  [/\bnamely\b/iu, 'the connective "namely"'],
  [/\bfootgun\b/iu, 'the word "footgun"'],
  [/\b(?:colour|behaviour|centre|grey|labell?ed|modelling|normalise|organise|whilst|amongst)\b/iu, 'a British spelling']
] as const

expect.extend({
  /**
   * Passes where `text` breaks none of the rules for published prose that a
   * pattern can check.
   */
  toBePublishedProse(text: string) {
    const broken = BREAKS.filter(([pattern]) => pattern.test(text)).map(([, rule]) => rule)

    return {
      message : () => `expected ${JSON.stringify(text)} `
                    + `${this.isNot ? 'to break' : 'to break no rule, but it carries'} `
                    + `${broken.join(', ') || 'a rule'}`,
      pass    : broken.length === 0
    }
  },

  /**
   * Passes where every fill in `fills` is one of the colors `palette` holds.
   */
  toDrawFrom(fills: readonly string[], palette: readonly string[]) {
    const strays  = fills.filter(fill => !palette.includes(fill))
    const outside = this.isNot ? 'every fill is one of them' : `${JSON.stringify(strays)} fall outside them`

    return {
      message : () => `expected ${this.isNot ? 'a fill outside' : 'every fill to be one of'} `
                    + `${JSON.stringify(palette)}, but ${outside}`,
      pass    : strays.length === 0
    }
  }
})

declare module 'vitest' {
  interface Matchers<R extends void | Promise<void> = void | Promise<void>, T = unknown> {
    toBePublishedProse : () => R
    toDrawFrom         : (palette: readonly string[]) => R
  }
}
