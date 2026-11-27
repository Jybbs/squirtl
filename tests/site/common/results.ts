import { vi } from 'vitest'

/**
 * Whether the stand-in below holds the seven runs the fixture holds or no run
 * at all.
 */
const held = vi.hoisted(() => ({ runs: false }))

vi.mock('../../../docs/.vitepress/lib/results/results.ts', async original => {
  const module  = await original<typeof import('../../../docs/.vitepress/lib/results/results.ts')>()
  const fixture = await import('../lib/results/fixtures/results.json')
  const none    = { comparisons: [], random: null, runs: [] }
  const shown   = () => (held.runs ? fixture.default : none) as unknown as typeof module.COMMITTED
  return {
    ...module,
    get COMMITTED() { return shown() },
    groupsOf: (results = shown()) => module.groupsOf(results)
  }
})

export { held }
