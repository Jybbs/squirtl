import { describe, expect, it } from 'vitest'

import PAGE        from '../../../../docs/pages/methods/search.md?raw'
import { Episode } from '../../../../docs/.vitepress/lib/game/episode.ts'
import { BUTTONS, type Button } from '../../../../docs/.vitepress/lib/game/rooms.ts'
import * as search from '../../../../docs/.vitepress/lib/methods/search.ts'
import SETTINGS    from '../../../../docs/.vitepress/lib/rendered/settings.json' with { type: 'json' }

type Group = Iteration['groups'][number]

type Iteration = search.Search['iterations'][number]

/**
 * The search the drawing plays.
 */
const { SEARCH } = search
/**
 * The words the page sets each count of its sentences in.
 */
const WORDS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten']
/**
 * Every copy of every iteration, beside its iteration.
 */
const COPIES = SEARCH.iterations.flatMap((iteration, n) => iteration.groups.map(group => ({ group, n })))
  .flatMap(({ group, n }) => group.copies.map(copy => ({ copy, n })))
/**
 * Each copy of every iteration beside its iteration and the key of the square
 * its rollout ends on.
 */
const ENDS = COPIES.map(({ copy, n }) => ({
  copy, n, square: episodeOf([...search.pathOf(SEARCH.nodes, copy.start), ...copy.presses]).key()
}))
/**
 * Every iteration beside its place.
 */
const ITERATIONS = SEARCH.iterations.map((iteration, n) => ({ iteration, n }))
/**
 * Every group of every iteration that kept a winner, beside its place in the
 * iteration and the iteration's.
 */
const KEPT = SEARCH.iterations.flatMap(({ groups }, n) => groups.map((group, g) => ({ g, group, n })))
  .filter(({ group }) => group.winner !== null)

/**
 * Reads the copy a group keeps as its winner: the live copy whose lineage pays
 * the most, and among those the one with the highest uncertainty.
 */
function bestOf(group: Group): search.Copy {
  const live = group.copies.filter(copy => !copy.dead)
  const most = Math.max(...live.map(copy => copy.totals.at(-1)!))
  return live.filter(copy => copy.totals.at(-1) === most)
    .toSorted((left, right) => right.uncertainty - left.uncertainty)[0]!
}

/**
 * Reads where a rollout from `copy`'s node leaves Blue, the text the screen
 * shows, the starter chosen, and the total, before its presses and after.
 */
function endsOf(copy: search.Copy): unknown[][] {
  const path = search.pathOf(SEARCH.nodes, copy.start)
  return [path, [...path, ...copy.presses]].map(presses => {
    const { at, chosen, place, script, speech, total } = episodeOf(presses)
    return [place, at, speech, script.length, chosen, total]
  })
}

/**
 * Plays `presses` into a fresh episode from the bedroom.
 */
function episodeOf(presses: readonly Button[]): Episode {
  const episode = new Episode()
  for (const press of presses) episode.press(press)
  return episode
}

/**
 * Plays `copy`'s rollout from its node, reading whether each press set a flag
 * the reward pays.
 */
function flagsOf(copy: search.Copy): boolean[] {
  const episode = episodeOf(search.pathOf(SEARCH.nodes, copy.start))
  return copy.presses.map(press => episode.press(press).some(each => each.term !== 'novelty'))
}

/**
 * Lists `node` and every node above it up to the root.
 */
function lineageOf(node: number): number[] {
  const parent = SEARCH.nodes[node]!.parent
  return parent === null ? [node] : [node, ...lineageOf(parent)]
}

/**
 * Reads the node each group of an iteration moves to: its winner's, the parent
 * of the one it began on where every copy died, and the one of those its
 * lineage pays most for every group where the iteration moves both.
 */
function nextOf(iteration: Iteration, nodes: search.Search['nodes'] = SEARCH.nodes): number[] {
  const own  = iteration.groups.map(group => group.winner === null
    ? parentOf(group, nodes)
    : group.copies[group.winner]!.node!)
  const best = own.reduce((top, node) => nodes[node]!.total > nodes[top]!.total ? node : top)
  return iteration.synced ? own.map(() => best) : own
}

/**
 * Reads the parent of the node a group's copies began on, the root for the
 * root itself.
 */
function parentOf(group: Group, nodes: search.Search['nodes']): number {
  return nodes[group.copies[0]!.start]!.parent ?? 0
}

/**
 * Counts the saved states each iteration keeps: the bedroom's and every node a
 * group has moved to, less those on no lineage of the nodes the groups move to.
 */
function savedBy(): number[] {
  let saved = new Set([0])
  return SEARCH.iterations.map(({ groups }) => {
    const starts = groups.map(group => group.next)
    const kept   = new Set(starts.flatMap(start => lineageOf(start)))
    saved        = new Set([...saved, ...starts].filter(node => kept.has(node)))
    return saved.size
  })
}

/**
 * Adds up the presses of every rollout through iteration `n`.
 */
function spentBy(n: number): number {
  return COPIES.filter(each => each.n <= n).reduce((sum, { copy }) => sum + copy.presses.length, 0)
}

/**
 * Lists the iterations whose saved states fall outside the tree's nodes.
 */
function strays(iterations: readonly Iteration[]): Iteration[] {
  return iterations.filter(each => each.saved < 1 || each.saved > each.nodes)
}

describe('the search', () => {
  it('reads the chance of a random press the settings declare', () => {
    expect(search.SIZES.epsilon).toBe(SETTINGS.search.epsilon)
  })

  it('ends once a copy sets the starter’s flag, its lineage the demonstration', () => {
    const { group, slot } = SEARCH.found
    const holder          = SEARCH.iterations.at(-1)!.groups[group]!.copies[slot]!
    const earlier         = COPIES.filter(each => each.n < search.LAST - 1)
      .filter(each => each.copy.term === 'goal')

    expect([holder.term, episodeOf(SEARCH.demonstration).total, earlier])
      .toStrictEqual(['goal', holder.totals.at(-1), []])
  })
})

describe('the search’s rollouts', () => {
  it.each(COPIES.filter(each => each.copy.term !== null))(
    'halts the rollout of iteration $n at the press setting a flag',
    ({ copy }) => {
      expect(flagsOf(copy).indexOf(true)).toBe(copy.presses.length - 1)
    }
  )

  it.each(COPIES.filter(each => each.copy.term === null))(
    'plays the rollout of iteration $n setting no flag to its length',
    ({ copy }) => {
      expect([flagsOf(copy).includes(true), copy.presses.length]).toStrictEqual([false, search.SIZES.presses])
    }
  )

  it.each(COPIES.filter(each => each.copy.dead))(
    'counts a rollout of iteration $n dead where it ends where it began, adding no node',
    ({ copy }) => {
      const [before, after] = endsOf(copy)

      expect([after, copy.node]).toStrictEqual([before, null])
    }
  )

  it.each(COPIES.filter(each => !each.copy.dead))(
    'keeps a rollout of iteration $n live, adding a node, where it ends off the screen it began on',
    ({ copy }) => {
      const [before, after] = endsOf(copy)

      expect(after).not.toStrictEqual(before)
      expect(copy.node).not.toBeNull()
    }
  )

  it('presses a random button in place of the held one at the chance the settings declare', () => {
    const held = COPIES.flatMap(({ copy }) => copy.presses.map(press => press === copy.held))
    const off  = held.filter(same => !same).length / held.length

    expect(off).toBeCloseTo(search.SIZES.epsilon * (1 - 1 / BUTTONS.length), 1)
  })
})

describe('the search’s groups', () => {
  it.each(KEPT)(
    'keeps as group $g’s winner in iteration $n the live copy paid most, then the most uncertain',
    ({ group }) => {
      expect(group.copies[group.winner!]).toBe(bestOf(group))
    }
  )

  it.each(ITERATIONS)(
    'moves every group of iteration $n to its winner, both to the better one every fourth',
    ({ iteration, n }) => {
      expect([iteration.synced, iteration.groups.map(group => group.next)])
        .toStrictEqual([(n + 1) % search.SIZES.sync === 0, nextOf(iteration)])
    }
  )

  it.each(ITERATIONS)(
    'rates each copy of iteration $n by how rarely the search has stood on its last square',
    ({ n }) => {
      const stood = ENDS.filter(each => each.n <= n).map(each => each.square)
      const ended = ENDS.filter(each => each.n === n)

      expect(ended.map(({ copy }) => copy.uncertainty))
        .toStrictEqual(ended.map(({ square }) => 1 / Math.sqrt(stood.filter(at => at === square).length)))
    }
  )

  it.each(ITERATIONS.slice(1))(
    'starts iteration $n’s rollouts from the nodes the last one moved its groups to',
    ({ iteration, n }) => {
      expect(iteration.groups.map(group => group.copies.map(copy => copy.start)))
        .toStrictEqual(SEARCH.iterations[n - 1]!.groups.map(group => group.copies.map(() => group.next)))
    }
  )
})

describe('the search’s figures', () => {
  it('counts the presses spent, the nodes grown, and the saved states each iteration keeps', () => {
    const { nodes } = SEARCH.iterations.at(-1)!

    expect([SEARCH.iterations.map(each => each.spent), nodes, strays(SEARCH.iterations)])
      .toStrictEqual([ITERATIONS.map(({ n }) => spentBy(n)), SEARCH.nodes.length, []])
  })

  it('keeps a saved state for each node a group moved to that stays on a lineage the groups stand on', () => {
    expect(SEARCH.iterations.map(each => each.saved)).toStrictEqual(savedBy())
  })

  it('moves a group whose copies all die to the parent of the node they began on', () => {
    const [iteration, nodes] = search.iterationsOf({ ...search.SIZES, particles: 2, seed: 97 })
      .take(search.LAST)
      .filter(([each]) => !each.synced)
      .find(([each]) => each.groups.some(group => group.winner === null))!
    const fell               = iteration.groups.filter(group => group.winner === null)

    expect(fell.map(group => group.next)).toStrictEqual(fell.map(group => parentOf(group, nodes)))
  })

  it('names on its page the defaults the settings declare and the drawing’s rollout length', () => {
    const { groups, particles, rollback: [fewest, most] } = SETTINGS.search
    const phrases = [
      `\`--search.groups\` defaults to ${groups} and \`--search.particles\` to ${particles}`,
      `by between ${WORDS[fewest!]} and ${WORDS[most!]} generations under the default \`--search.rollback\``,
      `rollouts of at most ${WORDS[search.SIZES.presses]} presses`
    ]

    expect(phrases.filter(phrase => !PAGE.includes(phrase))).toStrictEqual([])
  })

  it('keeps a group whose copies all die on the bedroom’s node there', () => {
    const [first] = search.iterationsOf({ ...search.SIZES, particles: 2, seed: 272 }).next().value
    const fell    = first.groups.filter(group => group.winner === null)

    expect(fell.length).toBeGreaterThan(0)
    expect(fell.map(group => [group.copies[0]!.start, group.next])).toStrictEqual(fell.map(() => [0, 0]))
  })

  it('fails by name where no copy sets the starter’s flag within its iterations', () => {
    expect(() => search.searchOf(search.SIZES, 2))
      .toThrow('The search sets no starter\'s flag within 2 iterations')
  })
})
