"""
Defines the population of a search, `Group`, the particles of one group, and
`Search`, which evolves every group through Algorithms 1 and 2 of Mhammedi
and Cohan's "Decoupling Exploration and Policy Optimization".
"""

from collections.abc  import Callable, Generator, Iterable, Sequence
from gymnasium.spaces import Box
from itertools        import batched
from numpy            import uint8, where
from numpy.random     import default_rng
from operator         import attrgetter

from squirtl.agent.schemas       import AgentSettings
from squirtl.environment.schemas import Recording, Snapshot
from squirtl.reward.schemas      import Event
from squirtl.runs.schemas        import SearchSettings
from squirtl.search.checkpoint   import SearchCheckpoint
from squirtl.search.novelty      import Novelty
from squirtl.search.schemas      import Ending, Frontier, Particle, Rollout
from squirtl.search.tree         import Tree


def highest(particles: Iterable[Particle]) -> Particle:
    """
    Finds the particle of `particles` ranking highest, the first of any
    tied.
    """
    return max(particles, key=attrgetter("rank"))


class Group:
    """
    One group of particles, the outer steps left to it in the iteration, and
    the winner it ranks highest.
    """

    def __init__(self, particle: Particle, particles: int):
        """
        Starts `particles` particles on `particle`.
        """
        self.particles = [particle] * particles
        self.remaining = 0

    @property
    def winner(self) -> Particle:
        """
        Finds the particle ranking highest, the first of any tied.
        """
        return highest(self.particles)

    def reset(self, particle: Particle):
        """
        Moves every particle of the group to `particle`.
        """
        self.particles = [particle] * len(self.particles)


class Search:
    """
    The search of Mhammedi and Cohan's Algorithm 2 over groups each evolving
    through their Algorithm 1, which `iterate` runs one iteration of. The
    coordinator draws every rollout before a worker plays it and reads every
    ending in the order it submitted them, so on the CPU one seed reaches
    one demonstration whichever worker runs which rollout.
    """

    def __init__(
        self,
        actions  : int,
        agent    : AgentSettings,
        goal     : Event,
        roll     : Callable[[Iterable[Rollout]], Iterable[Ending]],
        root     : Snapshot,
        seed     : int,
        settings : SearchSettings,
        space    : Box,
        steps    : int
    ):
        """
        Starts every particle on `root`, the root of an empty tree, with
        no reward.

        Args:
            actions : The actions a press chooses from.
            agent   : The settings naming the device and threads the
                      predictor runs on.
            goal    : The flag whose setting ends the search.
            roll    : Plays each rollout and returns its ending, in the
                      order they came.
            seed    : The unsigned 64-bit seed every random draw starts
                      from.
            space   : The frame stacks the predictor reads.
            steps   : The presses after which the search ends.
        """
        self.generator, sampling = default_rng(seed).spawn(2)

        start = Particle(
            node     = 0,
            reward   = 0.0,
            score    = 0.0,
            snapshot = root
        )

        self.actions = actions
        self.goal    = goal
        self.groups  = [
            Group(start, settings.particles) for _ in range(settings.groups)
        ]
        self.iterations = 0
        self.novelty    = Novelty(agent, sampling, seed, settings, space)
        self.presses    = 0
        self.roll       = roll
        self.settings   = settings
        self.steps      = steps
        self.tree       = Tree(root)
        self.winner     = start

    @property
    def checkpoint(self) -> SearchCheckpoint:
        """
        Gathers what a stopped search continues from at the end of an
        iteration, its arrays and networks uncopied.
        """
        return SearchCheckpoint(
            arrays   = self.tree.arrays | self.novelty.arrays,
            frontier = Frontier(
                groups     = [group.winner for group in self.groups],
                iterations = self.iterations,
                planning   = self.generator.bit_generator.state,
                presses    = self.presses,
                states     = self.tree.states,
                winner     = self.winner
            ),
            networks = self.novelty.networks
        )

    @property
    def demonstration(self) -> Recording:
        """
        Records the winner's path from the root as the `timer_div` the root
        started under and each press reaching the winner's node.
        """
        return Recording(
            presses   = self.tree.path(self.winner.node),
            timer_div = self.winner.snapshot.timer_div
        )

    @property
    def finished(self) -> bool:
        """
        Reads whether a particle has set the goal or the presses have
        reached `steps`.
        """
        return self.presses >= self.steps or any(
            self.goal in particle.snapshot.tally.events
            for group in self.groups
            for particle in group.particles
        )

    @property
    def reached(self) -> bool:
        """
        Reads whether the winner has set the goal, as it has once a particle
        sets it and the iteration consolidates, since the goal pays the most
        of any flag.
        """
        return self.goal in self.winner.snapshot.tally.events

    def advance(self, group: Group, played: Sequence[tuple[Rollout, Ending]]):
        """
        Stores what each rollout of `group` observed for the predictor and
        counts its presses, then runs one outer step's lines of Algorithm
        1 on its endings. Each survivor adds its child to the tree. Every
        dead particle moves to the winner, the survivor ranking highest, and
        where none survives, every particle rolls back instead. The winner's
        node then keeps a state, since a particle moved to it.
        """
        for rollout, ending in played:
            self.novelty.observe(ending.frames, rollout.snapshot)
            self.presses += len(ending.presses)

        group.remaining -= 1
        survivors        = [ending for _, ending in played if not ending.dead]

        if not survivors:
            self.rollback(group)

            return

        scores = iter(self.novelty.score(ending.snapshot for ending in survivors))
        moved  = [
            None if ending.dead else Particle(
                node     = self.tree.add(particle.node, ending.presses),
                reward   = ending.reward,
                score    = next(scores),
                snapshot = ending.snapshot
            )
            for particle, (_, ending) in zip(group.particles, played, strict=True)
        ]
        winner = highest(filter(None, moved))

        if len(survivors) < len(played):
            self.tree.states[winner.node] = winner.snapshot

        group.particles = [particle or winner for particle in moved]

    def consolidate(self):
        """
        Moves each group to its winner, keeping that node's state, makes the
        best of the winners and the last winner, scored afresh, the winner,
        and drops every kept state no particle's lineage holds.
        """
        for group in self.groups:
            winner = group.winner

            group.reset(winner)
            self.tree.states[winner.node] = winner.snapshot

        self.winner = highest(
            particles = (
                *(group.winner for group in self.groups),
                self.winner.model_copy(
                    update = {"score": self.novelty.score([self.winner.snapshot])[0]}
                )
            )
        )
        self.iterations += 1
        self.tree.states[self.winner.node] = self.winner.snapshot
        self.tree.retain(
            {self.winner.node, *(group.winner.node for group in self.groups)}
        )

    def draw(self, bounds: tuple[int, int]) -> int:
        """
        Draws a count uniformly from `bounds`, both ends included.
        """
        return self.generator.integers(*bounds, endpoint=True).item()

    def iterate(self) -> Generator[int, None, float | None]:
        """
        Runs one iteration of Algorithm 2, yielding the presses taken after
        each outer step. A group ranking below the winner on reward first
        moves to it, and each group then draws its outer steps. Once each
        has played them, or the search has finished, each group consolidates
        on its winner and the best of those and the last winner, scored
        afresh, becomes the winner. The predictor then trains on what the
        iteration observed.

        Returns:
            The mean loss over the predictor's updates, as `Novelty.train`
            returns it.
        """
        for group in self.groups:
            if group.winner.reward < self.winner.reward:
                group.reset(self.winner)

            group.remaining = self.draw(self.settings.outer_steps)

        while not self.finished and (
            active := [group for group in self.groups if group.remaining]
        ):
            self.step(active)

            yield self.presses

        self.consolidate()

        return self.novelty.train(self.presses)

    def plan(self) -> bytes:
        """
        Draws one rollout's presses, its count from `inner_steps`, each
        press holding one action drawn for the rollout or at `epsilon` a
        random one, as Mhammedi and Cohan's section 4.4 commits a particle
        to one action.
        """
        presses = self.draw(self.settings.inner_steps)

        return (
            where(
                self.generator.random(presses) < self.settings.epsilon,
                self.generator.integers(self.actions, size=presses),
                self.generator.integers(self.actions)
            )
            .astype(uint8)
            .tobytes()
        )

    def restore(self, checkpoint: SearchCheckpoint):
        """
        Loads `checkpoint` into the tree, the predictor, the groups, and the
        generator, so the search goes on as an unbroken one would.

        Raises:
            ValueError: Where its arrays or networks differ from those this
                        search builds, as `Novelty.load` raises.
        """
        frontier = checkpoint.frontier

        self.novelty.load(checkpoint.arrays, checkpoint.networks)
        self.tree.load(checkpoint.arrays, frontier.states)
        self.generator.bit_generator.state = frontier.planning
        self.iterations = frontier.iterations
        self.presses    = frontier.presses
        self.winner     = frontier.winner

        for group, particle in zip(self.groups, frontier.groups, strict=True):
            group.reset(particle)

    def rollback(self, group: Group):
        """
        Moves each particle of `group` to a random ancestor drawn from
        `rollback` generations up, as Algorithm 1 does once all are dead. A
        worker brings back each distinct ancestor from the nearest state the
        tree keeps, and the tree then keeps its state, since particles moved
        to it.
        """
        nodes = [
            self.tree.ancestor(self.draw(self.settings.rollback), particle.node)
            for particle in group.particles
        ]
        unique   = list(dict.fromkeys(nodes))
        endings  = list(self.roll(map(self.tree.restoring, unique)))
        scores   = self.novelty.score(ending.snapshot for ending in endings)
        restored = {
            node: Particle(
                node     = node,
                reward   = ending.reward,
                score    = score,
                snapshot = ending.snapshot
            )
            for node, ending, score in zip(unique, endings, scores, strict=True)
        }

        for node, particle in restored.items():
            self.tree.states[node] = particle.snapshot

        group.particles = [restored[node] for node in nodes]

    def step(self, active: Sequence[Group]):
        """
        Plays one outer step of each of `active`, one rollout per particle
        across the workers, and advances each group on its endings.
        """
        rollouts = [
            Rollout(presses=self.plan(), snapshot=particle.snapshot)
            for group in active
            for particle in group.particles
        ]

        for group, played in zip(
            active,
            batched(zip(rollouts, self.roll(rollouts)), self.settings.particles),
            strict = True
        ):
            self.advance(group, played)
