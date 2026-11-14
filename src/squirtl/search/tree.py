"""
Defines `LineageTree`, the lineage tree of a search, Mhammedi and Cohan's
section 4.1 with each node held as its parent and the presses reaching it,
every node kept for the whole search where section 4.1 prunes a node once no
particle occupies it or any node below it.
"""

from array           import array
from collections.abc import Iterable, Iterator, Mapping
from itertools       import takewhile
from numpy           import asarray, ndarray

from squirtl.environment.schemas import Snapshot
from squirtl.search.schemas      import SearchRollout


class LineageTree:
    """
    Every node a search has reached, the root numbered 0 and each later
    node numbered in the order the search added it. A node holds its parent
    and the presses of the rollout that reached it, which replay from an
    ancestor to the same state byte for byte, and a `Snapshot` only where a
    particle moved to it, so a node's state costs one compressed save where
    one is needed at all.
    """

    def __init__(self, root: Snapshot):
        """
        Starts the tree on the node `root` holds, which it keeps for good.
        """
        self.ends    = array("Q", [0])
        self.parents = array("Q", [0])
        self.presses = bytearray()
        self.states  = {0: root}

    def __len__(self) -> int:
        """
        Counts the nodes.
        """
        return len(self.parents)

    @property
    def arrays(self) -> dict[str, ndarray]:
        """
        Copies each array holding the nodes under its name, leaving out
        the kept states, which a checkpoint writes as JSON. Each is a copy,
        since an `array` or a `bytearray` refuses to grow while a view of
        it lives.
        """
        return {
            "ends"    : asarray(self.ends).copy(),
            "parents" : asarray(self.parents).copy(),
            "presses" : asarray(self.presses).copy()
        }

    @property
    def nbytes(self) -> int:
        """
        Totals the bytes the nodes and the compressed states hold.
        """
        return (
            sum(
                memoryview(nodes).nbytes for nodes in (
                    self.ends, self.parents, self.presses
                )
            )
            + sum(
                len(state.frames) + len(state.state) for state in self.states.values()
            )
        )

    def add(self, parent: int, presses: bytes) -> int:
        """
        Adds the child of `parent` that `presses` reach.

        Returns:
            The child's number.
        """
        self.parents.append(parent)
        self.presses += presses
        self.ends.append(len(self.presses))

        return len(self) - 1

    def ancestor(self, generations: int, node: int) -> int:
        """
        Moves `generations` up from `node`, stopping at the root.

        Returns:
            The number of the node reached.
        """
        for _ in range(generations):
            node = self.parents[node]

        return node

    def between(self, ancestor: int, node: int) -> bytes:
        """
        Joins the presses reaching `node` from `ancestor`, in the order
        they played.
        """
        return b"".join(
            self.presses[self.ends[step - 1]:self.ends[step]]
            for step in reversed([*takewhile(ancestor.__ne__, self.lineage(node))])
        )

    def lineage(self, node: int) -> Iterator[int]:
        """
        Walks from `node` up to the root, yielding each node on the way and
        the root last.
        """
        while node:
            yield node

            node = self.parents[node]

        yield 0

    def load(self, arrays: Mapping[str, ndarray], states: Mapping[int, Snapshot]):
        """
        Takes the nodes from the `arrays` a checkpoint holds and keeps
        `states` in place of those the tree holds.
        """
        self.ends    = array("Q", arrays["ends"].tobytes())
        self.parents = array("Q", arrays["parents"].tobytes())
        self.presses = bytearray(arrays["presses"].tobytes())
        self.states  = dict(states)

    def path(self, node: int) -> bytes:
        """
        Joins the presses reaching `node` from the root, in the order they
        played.
        """
        return self.between(0, node)

    def restoring(self, node: int) -> SearchRollout:
        """
        Builds the rollout that brings back `node`, the presses from the
        nearest node at or above it keeping a state.
        """
        kept = next(filter(self.states.__contains__, self.lineage(node)))

        return SearchRollout(
            halting  = False,
            presses  = self.between(kept, node),
            snapshot = self.states[kept]
        )

    def retain(self, occupied: Iterable[int]):
        """
        Drops each kept state on no lineage of `occupied`, the nodes the
        particles occupy, since no rollback can reach it.
        """
        lineages = {ancestor for node in occupied for ancestor in self.lineage(node)}

        self.states = {
            node: state for node, state in self.states.items() if node in lineages
        }
