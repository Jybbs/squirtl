"""
Pins the lineage tree of a search, covering:

- The number each node takes, and the presses joined along its lineage
- Moving up a lineage, which stops at the root
- The nearest kept state a node is brought back from
- Dropping each kept state no occupied lineage holds
- What the tree counts in bytes, and its arrays loading back, which leave
  it free to grow while a checkpoint holds them
"""

from common.search import snapshot
from pytest        import fixture, mark, param

from squirtl.search.tree import LineageTree


@fixture
def tree() -> LineageTree:
    """
    Builds a tree holding a root, its children 1 and 3, and 2 beneath 1 and
    4 beneath 2, each reached by presses naming it.
    """
    built = LineageTree(snapshot())

    built.add(0, b"\x01\x01")
    built.add(1, b"\x02")
    built.add(0, b"\x03\x03\x03")
    built.add(2, b"\x04")

    return built


def test_a_lineage_walks_up_to_the_root_last(tree: LineageTree):
    """
    Asserts that a lineage yields the node, each ancestor, and the root
    last.
    """
    assert [*tree.lineage(4)] == [4, 2, 1, 0]


def test_a_new_tree_holds_its_root_alone():
    """
    Asserts that a new tree holds one node, whose state it keeps and whose
    path is empty.
    """
    root = snapshot()
    tree = LineageTree(root)

    assert (len(tree), tree.states, tree.path(0)) == (1, {0: root}, b"")


@mark.parametrize(
    ("node", "path"),
    [
        param(0, b"",                 id="the-root"),
        param(1, b"\x01\x01",         id="a-child"),
        param(3, b"\x03\x03\x03",     id="its-sibling"),
        param(4, b"\x01\x01\x02\x04", id="a-deep-node")
    ]
)
def test_a_nodes_path_joins_the_presses_of_its_lineage_in_order(
    node : int,
    path : bytes,
    tree : LineageTree
):
    """
    Asserts that a node's path holds the presses reaching it from the root
    in the order they played, and none of any other branch.
    """
    assert tree.path(node) == path


def test_a_tree_goes_on_growing_while_its_arrays_are_held(tree: LineageTree):
    """
    Asserts that adding a node while its arrays are still held leaves those
    arrays as they were rather than raising on the view of a resized buffer.
    """
    arrays = tree.arrays

    tree.add(0, b"\x05")

    assert (len(arrays["parents"]), len(arrays["presses"]), len(tree)) == (5, 7, 6)


@mark.parametrize(
    ("generations", "reached"),
    [
        param(0, 4, id="none"),
        param(1, 2, id="one"),
        param(3, 0, id="to-the-root"),
        param(9, 0, id="past-the-root")
    ]
)
def test_an_ancestor_moves_up_and_stops_at_the_root(
    generations : int,
    reached     : int,
    tree        : LineageTree
):
    """
    Asserts that moving up reaches the node that many generations above, and
    no further than the root.
    """
    assert tree.ancestor(generations, 4) == reached


def test_each_node_takes_the_next_number(tree: LineageTree):
    """
    Asserts that a node added next takes the number after the last.
    """
    assert (len(tree), tree.add(3, b"\x05"), len(tree)) == (5, 5, 6)


def test_restoring_a_node_keeping_a_state_presses_nothing(tree: LineageTree):
    """
    Asserts that the rollout bringing back a node keeping its own state
    holds no press.
    """
    state = snapshot(shade=5)

    tree.states[4] = state

    assert (tree.restoring(4).presses, tree.restoring(4).snapshot) == (b"", state)


def test_restoring_a_node_plays_from_the_nearest_state_kept_above_it(tree: LineageTree):
    """
    Asserts that the rollout bringing back a node starts from the nearest
    kept state at or above it, plays every press between them, and plays on
    whatever they earn.
    """
    state = snapshot(shade=5)

    tree.states[2] = state
    rollout        = tree.restoring(4)

    assert (
        rollout.halting, rollout.presses, rollout.snapshot
    ) == (False, b"\x04", state)


def test_retaining_drops_each_state_on_no_occupied_lineage(tree: LineageTree):
    """
    Asserts that retaining the occupied nodes keeps each state on a lineage
    of one of them, the root's included, and drops the rest.
    """
    for node in (1, 3, 4):
        tree.states[node] = snapshot(shade=node)

    tree.retain([4])

    assert [*tree.states] == [0, 1, 4]


def test_the_arrays_load_into_a_tree_reading_the_same(tree: LineageTree):
    """
    Asserts that a tree loading the arrays and the states of another holds
    the same nodes, paths, and states.
    """
    loaded = LineageTree(snapshot())

    tree.states[2] = snapshot(shade=5)
    loaded.load(tree.arrays, tree.states)

    assert (
        len(loaded),
        loaded.path(4),
        loaded.states
    ) == (5, b"\x01\x01\x02\x04", tree.states)


def test_the_bytes_count_the_nodes_and_the_compressed_states(tree: LineageTree):
    """
    Asserts that the bytes count each of the 5 nodes' parent and end at 8
    bytes each, the 7 presses, and both compressed members of each state.
    """
    root = tree.states[0]

    assert tree.nbytes == 5 * 16 + 7 + len(root.frames) + len(root.state)
