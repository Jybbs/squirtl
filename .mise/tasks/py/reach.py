"""
Prints the pytest arguments the files changed since a merge base reach
through the suite's imports and fixture requests, one a line, taking the
merge base first and each changed path after it.

A changed module reaches each test module and each subpackage conftest
folder loading it, by an import or by walking the package holding it by
computed name. An import counts through any chain among the package's
modules and the suite's, function-local imports, package `__init__` files,
helpers, and quoted dotted `squirtl` names included. `tests/py/conftest.py`
passes a change on only to the tests requesting a fixture that reads what
changed, and the script prints `tests/py` alone where a change reaches every
test.
"""

from ast             import (
    AST, AnnAssign, Assign, AsyncFunctionDef, Attribute, Call, ClassDef, Constant, FunctionDef,
    Import, ImportFrom, List, Load, Module, Name, Store, Tuple, dump, expr, get_docstring, parse, stmt, unparse, walk
)
from collections     import Counter, defaultdict
from collections.abc import Iterable, Iterator
from copy            import replace
from dataclasses     import dataclass
from enum            import StrEnum, auto
from functools       import cache, cached_property
from itertools       import accumulate
from pathlib         import Path
from re              import compile, escape, search
from subprocess      import run
from sys             import argv, stdout
from typing          import Self

DOTTED  = compile(r"squirtl(?:\.\w+)+")
LOADERS = compile(r"\b(?:import_module|iter_modules|walk_packages)\b")
PATHS   = compile(r"\b([A-Za-z_][\w.]*)\.__path__\b")
ROOT    = "tests/py/conftest.py"


class Fixture(StrEnum):
    """
    The kinds of fixture pytest's `fixture` decorator declares.
    """

    AUTOUSE = auto()
    PLAIN   = auto()


class Whole(Exception):
    """
    Raised where a change reaches every test, which `Suite.select` returns
    as the one argument `tests/py`.
    """


@cache
def located(dotted: str) -> str | None:
    """
    Finds the file importing `dotted` loads, at the path `source` builds.

    Returns:
        The file's path from the worktree root, or `None` where no module
        or package of that name sits there.
    """
    base = source(dotted)

    return next(
        (
            path.as_posix()
            for path in (base.with_suffix(".py"), base / "__init__.py")
            if path.is_file()
        ),
        None
    )


def imported(node: Import | ImportFrom) -> Iterator[tuple[str, str]]:
    """
    Yields each name an absolute import statement binds, beside the dotted
    name of the module or attribute it binds.
    """
    for alias in node.names:
        if isinstance(node, Import):
            first = alias.name.partition(".")[0]

            yield (alias.asname, alias.name) if alias.asname else (first, first)
        elif not node.level:
            yield alias.asname or alias.name, f"{node.module}.{alias.name}"


def main(base: str, *changed: str):
    """
    Prints each pytest argument the `changed` files reach since `base`, one
    a line, and nothing where they reach no test.
    """
    stdout.writelines(
        f"{argument}\n" for argument in Suite.read().select(base, changed)
    )


def marked(
    mark : str,
    node : AsyncFunctionDef | ClassDef | FunctionDef
) -> Iterator[Call]:
    """
    Yields each call of the pytest mark named `mark` among the decorators
    of `node`.
    """
    for decorator in node.decorator_list:
        if (
            isinstance(decorator, Call)
            and getattr(decorator.func, "attr", None) == mark
        ):
            yield decorator


def names(node: expr | None) -> set[str]:
    """
    Reads the comma-separated names a string, or a list or tuple of strings,
    holds, as `parametrize` and `usefixtures` read their first argument.
    """
    if isinstance(node, Constant) and isinstance(node.value, str):
        return {name for part in node.value.split(",") if (name := part.strip())}

    if isinstance(node, (List, Tuple)):
        return {name for element in node.elts for name in names(element)}

    return set()


def packages(dotted: str) -> Iterator[str]:
    """
    Yields the `__init__` file of each package above `dotted`, each of which
    importing `dotted` runs first.
    """
    for prefix in [*prefixes(dotted)][:-1]:
        if (path := located(prefix)) and path.endswith("__init__.py"):
            yield path


def parameters(function: FunctionDef | AsyncFunctionDef) -> set[str]:
    """
    Reads the names of every parameter `function` declares, which pytest
    resolves as fixture requests.
    """
    arguments = function.args

    return {
        argument.arg
        for argument in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs)
    }


def prefixes(dotted: str) -> Iterator[str]:
    """
    Yields each prefix of `dotted` ending at a dot or at its end, shortest
    first, `dotted` itself last.
    """
    return accumulate(dotted.split("."), "{}.{}".format)


def pytestmark(module: Module) -> set[str]:
    """
    Reads the fixtures each `usefixtures` mark the `pytestmark` assignment
    of `module` holds lists, which pytest applies to every test the module
    defines.
    """
    return used(
        calls = (call
        for node in module.body
        if isinstance(node, Assign)
        and "pytestmark" in {getattr(target, "id", None) for target in node.targets}
        for call in walk(node.value)
        if isinstance(call, Call) and getattr(call.func, "attr", None) == "usefixtures")
    )


def requests(test: AsyncFunctionDef | FunctionDef) -> tuple[set[str], set[str]]:
    """
    Reads the fixtures `test` requests through its parameters and its
    `usefixtures` marks, beside the parameters a `parametrize` mark fills
    directly rather than through `indirect`.

    Returns:
        The names requested, beside the names `parametrize` fills directly,
        which hide a fixture of that name from every fixture `test` reaches.
    """
    direct = set()

    for call in marked("parametrize", test):
        indirect = next(
            (keyword.value for keyword in call.keywords if keyword.arg == "indirect"),
            None
        )

        if not (isinstance(indirect, Constant) and indirect.value is True):
            direct |= names(call.args[0] if call.args else None) - names(indirect)

    return parameters(test) | used(marked("usefixtures", test)), direct


def source(dotted: str) -> Path:
    """
    Finds the path a module or package named `dotted` sits at without its
    suffix, under `src/` for the package and under `tests/py/` for every
    other name, since `[tool.pytest].pythonpath` names `tests/py`.
    """
    parts = dotted.split(".")

    return Path("src" if parts[0] == "squirtl" else "tests/py", *parts)


def undocumented(node: Module | stmt) -> Module | stmt:
    """
    Copies `node` without the docstring opening its body, or returns it as
    it is where its body opens on another statement.
    """
    return (
        replace(node, body=node.body[1:]) if get_docstring(node) is not None else node
    )


@dataclass(frozen=True)
class Conftest:
    """
    The module `tests/py/conftest.py` holds, as parsed from one side of a
    change to it or from the working tree.
    """

    module: Module

    @cached_property
    def bound(self) -> set[tuple[str, str]]:
        """
        Reads each name an import line binds, beside the dotted name of what
        it binds.
        """
        return {
            (alias.asname or alias.name.split(".")[0], alias.name)
            if isinstance(node, Import)
            else (
                alias.asname or alias.name,
                f"{'.' * node.level}{node.module}.{alias.name}"
            )
            for node in self.module.body
            if isinstance(node, (Import, ImportFrom))
            for alias in node.names
        }

    @cached_property
    def definitions(self) -> dict[str, tuple[stmt, str]]:
        """
        Reads each function, class, and assigned name the module defines,
        beside the statement defining it and that statement dumped through
        `ast.dump` without its docstring, which leaves out every line
        number, so moving a definition or rewording its docstring leaves the
        dump as it was.
        """
        definitions = {}

        for node in self.module.body:
            match node:
                case FunctionDef() | AsyncFunctionDef() | ClassDef():
                    definitions[node.name] = node, dump(undocumented(node))
                case Assign() | AnnAssign():
                    for name in walk(node):
                        if isinstance(name, Name) and isinstance(name.ctx, Store):
                            definitions[name.id] = node, dump(node)

        return definitions

    @cached_property
    def functions(self) -> dict[str, tuple[Fixture | None, set[str]]]:
        """
        Reads each top-level function of the module beside its `Fixture`
        kind and every name its definition reads, decorators included.
        """
        return {
            node.name: (
                kind(node),
                {
                    name.id
                    for name in walk(node)
                    if isinstance(name, Name) and isinstance(name.ctx, Load)
                }
            )
            for node in self.module.body
            if isinstance(node, (AsyncFunctionDef, FunctionDef))
        }

    @cached_property
    def rest(self) -> Counter[str]:
        """
        Counts the dump of each statement that is neither an import, a
        definition, nor the module's docstring.
        """
        return Counter(
            dump(node)
            for node in undocumented(self.module).body
            if not isinstance(
                node,
                (
                    AnnAssign, Assign, AsyncFunctionDef, ClassDef,
                    FunctionDef, Import, ImportFrom
                )
            )
        )

    def changes(self, other: Self) -> set[str]:
        """
        Finds the fixtures the change from this side to `other` touches,
        meaning each fixture whose definition differs between the sides and
        each fixture reading a name an import line binds differently.

        Raises:
            Whole: Where the change touches an autouse fixture, a `pytest_`
                   hook, a module-level name a fixture reads, or a statement
                   other than an import or a definition.
        """
        if self.rest != other.rest:
            raise Whole

        fixtures, read = set(), set()
        rebound        = {name for name, _ in self.bound ^ other.bound}

        for side, opposite in ((self, other), (other, self)):
            for name, (node, dumped) in side.definitions.items():
                if dumped == opposite.definitions.get(name, (None, ""))[1]:
                    continue

                found = kind(node)

                if name.startswith("pytest_") or found is Fixture.AUTOUSE:
                    raise Whole

                (fixtures if found else read).add(name)

        if any(side.reading(read) for side in (self, other)):
            raise Whole

        return fixtures | self.reading(rebound) | other.reading(rebound)

    def reading(self, read: set[str]) -> set[str]:
        """
        Follows each top-level function reading a name in `read`, directly
        or through another such function, to the fixtures among them.

        Returns:
            The fixtures reading one of `read`.

        Raises:
            Whole: Where an autouse fixture or a `pytest_` hook reads one.
        """
        reading = set(read)

        while found := {
            function for function, (_, reads) in self.functions.items()
            if reads & reading
        } - reading:
            reading |= found

        reached = reading & self.functions.keys()

        if any(
            name.startswith("pytest_") or self.functions[name][0] is Fixture.AUTOUSE
            for name in reached
        ):
            raise Whole

        return {name for name in reached if self.functions[name][0]}


@dataclass(frozen=True)
class Binding:
    """
    One file a module of the suite or the package loads, with the name an
    import statement binds to it, or `None` for a package `__init__` the
    import runs on the way, a file under a package walked by computed name,
    or a module a string names, which `quoted` marks.
    """

    target : str
    name   : str | None = None
    quoted : bool       = False


def used(calls: Iterable[Call]) -> set[str]:
    """
    Reads the fixture names each `usefixtures` call in `calls` lists.
    """
    return {name for call in calls for argument in call.args for name in names(
        node = argument
    )}


def bindings(nodes: Iterable[AST]) -> Iterator[Binding]:
    """
    Yields each file an import statement among `nodes` loads, and the module
    each dotted `squirtl` name quoted in a string names, read as the longest
    prefix naming a module, leaving out each relative import and each import
    of a module neither `src/` nor `tests/py/` holds.
    """
    for node in nodes:
        match node:
            case Import():
                for alias in node.names:
                    if target := located(alias.name):
                        yield Binding(target, alias.asname or alias.name.split(".")[0])
                        yield from (Binding(init) for init in packages(alias.name))
            case ImportFrom(module=str(), level=0):
                package = located(node.module)

                yield from (Binding(init) for init in packages(node.module))

                for alias in node.names:
                    bound = alias.asname or alias.name

                    if target := located(f"{node.module}.{alias.name}"):
                        yield Binding(target, bound)
                    elif package:
                        yield Binding(package, bound)

                        if package.endswith("__init__.py") and (
                            source := reexported(alias.name, package)
                        ):
                            yield Binding(source, bound)
            case Constant(value=str()) if found := DOTTED.match(node.value):
                yield from quoted(found.group(0))


def closure(
    direct    : set[str],
    levels    : list[dict[str, tuple[set[str], Fixture]]],
    requested : set[str]
) -> set[str]:
    """
    Resolves each fixture in `requested`, and each autouse fixture of every
    level, through `levels`, the fixtures each scope defines from the test's
    own outward to `tests/py/conftest.py`, where pytest takes the nearest
    definition and a fixture requesting its own name takes the next one out.

    Returns:
        The fixtures of `tests/py/conftest.py` the test reaches, with each name
        no level defines, which a fixture `tests/py/conftest.py` removed leaves.
    """
    stack = [(name, 0) for name in requested] + [
        (name, index)
        for index, level in enumerate(levels)
        for name, (_, found) in level.items()
        if found is Fixture.AUTOUSE
    ]
    reached, seen = set(), set()

    while stack:
        name, start = stack.pop()

        if (name, start) in seen or name in direct:
            continue

        seen.add((name, start))

        for index in range(start, len(levels)):
            if name in levels[index]:
                if index == len(levels) - 1:
                    reached.add(name)

                stack += [
                    (needed, index + 1 if needed == name else 0)
                    for needed in levels[index][name][0]
                ]
                break
        else:
            reached.add(name)

    return reached


def defined(body: Iterable[stmt]) -> dict[str, tuple[set[str], Fixture]]:
    """
    Reads each fixture `body` defines.

    Returns:
        Each fixture's name beside the fixtures its parameters request and its
        `Fixture` kind.
    """
    return {
        node.name: (parameters(node), found)
        for node in body
        if isinstance(node, (AsyncFunctionDef, FunctionDef)) and (found := kind(node))
    }


@cache
def reexported(name: str, package: str) -> str | None:
    """
    Finds the module the package `__init__` at `package` imports `name`
    from, or `None` where it imports no such name.
    """
    return next(
        (
            located(node.module)
            for node in walk(parse(Path(package).read_text(encoding="utf-8")))
            if isinstance(node, ImportFrom)
            and node.module
            and any((alias.asname or alias.name) == name for alias in node.names)
        ),
        None
    )


def kind(function: stmt) -> Fixture | None:
    """
    Reads whether `function` carries pytest's `fixture` decorator, bare or
    called, and whether the call sets `autouse`.

    Returns:
        The kind of fixture, or `None` where no decorator is `fixture`.
    """
    for decorator in getattr(function, "decorator_list", ()):
        target = decorator.func if isinstance(decorator, Call) else decorator

        if getattr(target, "attr", getattr(target, "id", None)) == "fixture":
            autouse = isinstance(decorator, Call) and any(
                keyword.arg == "autouse" and getattr(keyword.value, "value", False)
                for keyword in decorator.keywords
            )

            return Fixture.AUTOUSE if autouse else Fixture.PLAIN

    return None


@dataclass(frozen=True)
class Suite:
    """
    Every module under `tests/py/` outside a `fixtures/` folder, each
    parsed, keyed by its path from the worktree root.
    """

    trees: dict[str, Module]

    @cached_property
    def imports(self) -> dict[str, set[Binding]]:
        """
        Reads each file every module under `tests/py/` and `src/` loads, by
        an import or by walking a package, keyed by the module's path.
        """
        trees = {
            path.as_posix(): parse(path.read_text(encoding="utf-8"))
            for path in Path("src").rglob("*.py")
        } | self.trees

        return {
            path: {*bindings(nodes := [*walk(tree)]), *walked(nodes)}
            for path, tree in trees.items()
        }

    @cached_property
    def loaders(self) -> dict[str, set[str]]:
        """
        Inverts `imports`, keying each file loaded by the modules loading
        it directly.
        """
        loaders = defaultdict(set)

        for path, found in self.imports.items():
            for binding in found:
                loaders[binding.target].add(path)

        return loaders

    def chain(self, path: str) -> list[dict[str, tuple[set[str], Fixture]]]:
        """
        Reads the fixtures each scope a test module at `path` sees defines,
        the module itself first and then each conftest from its folder
        outward, `tests/py/conftest.py` last.
        """
        conftests = ((folder / "conftest.py").as_posix() for folder in Path(
            path
        ).parents[:-2])

        return [
            defined(self.trees[path].body),
            *(
                defined(self.trees[conftest].body if conftest in self.trees else ())
                for conftest in conftests
            )
        ]

    def collected(
        self,
        body      : list[stmt],
        inherited : set[str],
        levels    : list[dict[str, tuple[set[str], Fixture]]],
        path      : str,
        prefix    : tuple[str, ...]
    ) -> Iterator[tuple[str, set[str]]]:
        """
        Yields each test function `body` holds, descending into each
        `Test` class with its own fixtures as the nearest scope and its
        `usefixtures` marks added to `inherited`.
        """
        for node in body:
            if isinstance(node, ClassDef) and node.name.startswith("Test"):
                yield from self.collected(
                    node.body,
                    inherited | used(marked("usefixtures", node)),
                    [defined(node.body), *levels],
                    path,
                    (*prefix, node.name)
                )
            elif (
                isinstance(node, (AsyncFunctionDef, FunctionDef))
                and node.name.startswith("test")
                and not kind(node)
            ):
                requested, direct = requests(node)

                yield (
                    "::".join((path, *prefix, node.name)),
                    closure(direct, levels, requested | inherited)
                )

    def edited(self, base: str) -> set[str]:
        """
        Finds the fixtures of `tests/py/conftest.py` the change since `base`
        touches, reading both sides of it so a fixture the change removes
        counts beside one it adds or edits.

        Raises:
            Whole: Where the change reaches every test, per
                   `Conftest.changes`.
        """
        shown = run(
            ["git", "show", f"{base}:{ROOT}"], capture_output=True, text=True
        )
        old = parse(shown.stdout if shown.returncode == 0 else "")

        return Conftest(old).changes(Conftest(self.trees.get(ROOT) or parse("")))

    def importers(self, changed: str) -> tuple[set[str], set[str]]:
        """
        Finds what loading the changed file `changed` reaches, meaning
        each test module loading it, the folder of each subpackage conftest
        loading it, and each fixture of `tests/py/conftest.py` reading a
        name that conftest binds to it.

        Returns:
            The modules and folders, beside the fixtures.

        Raises:
            Whole: Where the change removes `changed`, which leaves no
                   import of it to resolve, where `pyproject.toml` names
                   a helper loading it or a start-file callable whose
                   module loads it, or where `tests/py/conftest.py` loads
                   it through a package `__init__`, a quoted name outside
                   a function, a package it walks, or a name an autouse
                   fixture or a hook reads.
        """
        if not Path(changed).is_file():
            raise Whole

        loading  = self.loading(changed)
        manifest = Path("pyproject.toml").read_text(encoding="utf-8")
        paths    = set()

        if (
            (started := search(r'template\s*=\s*"([\w.]+):', manifest))
            and located(started[1]) in loading
        ):
            raise Whole

        for path in self.trees.keys() & loading - {ROOT}:
            if path.startswith("tests/py/common/"):
                dotted = (
                    path.removeprefix("tests/py/")
                        .removesuffix(".py")
                        .replace("/", ".")
                )

                if search(rf"\b{escape(dotted)}\b", manifest):
                    raise Whole
            elif path.endswith("/conftest.py"):
                paths.add(path.removesuffix("/conftest.py"))
            else:
                paths.add(path)

        return paths, self.read_from_root(loading)

    def loading(self, changed: str) -> set[str]:
        """
        Follows `loaders` outward from `changed` through every chain of
        imports, a cycle among them included.

        Returns:
            Each module loading `changed`, directly or through another,
            with `changed` itself.
        """
        loading, pending = {changed}, [changed]

        while pending:
            found    = self.loaders.get(pending.pop(), set()) - loading
            loading |= found
            pending += found

        return loading

    @classmethod
    def read(cls) -> Self:
        """
        Parses each module under `tests/py/`, skipping the `fixtures/`
        folders `[tool.pytest].norecursedirs` names, whose files are inputs.
        """
        return cls(
            {
                path.as_posix(): parse(path.read_text(encoding="utf-8"))
                for path in sorted(Path("tests/py").rglob("*.py"))
                if "fixtures" not in path.parts
            }
        )

    def read_from_root(self, loading: set[str]) -> set[str]:
        """
        Finds the fixtures of `tests/py/conftest.py` reading a name it
        binds to a module in `loading`, the files loading a changed one, or
        defining a function whose body quotes a name of one.

        Raises:
            Whole: Where the conftest loads one through a package
                   `__init__`, a quoted name outside a function, or a
                   package it walks, or an autouse fixture or a hook reads
                   the name bound.
        """
        if ROOT not in self.trees:
            return set()

        root = self.trees[ROOT]
        read = set()

        if any(binding.target in loading for binding in walked(walk(root))):
            raise Whole

        for node in root.body:
            for binding in bindings(walk(node)):
                if binding.target not in loading:
                    continue

                if binding.name:
                    read.add(binding.name)
                elif (
                    binding.quoted
                    and isinstance(node, (AsyncFunctionDef, FunctionDef))
                ):
                    read.add(node.name)
                else:
                    raise Whole

        return Conftest(root).reading(read)

    def select(self, base: str, changed: Iterable[str]) -> list[str]:
        """
        Gathers what each of the `changed` files reaches, the root conftest
        through `edited` and every other file through `importers`, and the
        tests requesting each fixture so reached outside a path already
        selected.

        Returns:
            The test modules, folders, and node IDs, sorted, or `tests/py`
            alone where a change reaches every test.
        """
        paths, fixtures = set(), set()

        try:
            for path in changed:
                if path == ROOT:
                    fixtures |= self.edited(base)
                else:
                    found, read = self.importers(path)
                    paths      |= found
                    fixtures   |= read
        except Whole:
            return ["tests/py"]

        nodes = {node for node, reached in self.tests() if reached & fixtures}

        return sorted(
            path
            for path in paths | nodes
            if not any(path.startswith((f"{outer}/", f"{outer}::")) for outer in paths)
        )

    def tests(self) -> Iterator[tuple[str, set[str]]]:
        """
        Yields the node ID of each test function the suite collects, beside
        the fixtures of `tests/py/conftest.py` it reaches.
        """
        for path, tree in self.trees.items():
            if path.startswith("tests/py/common/") or path.endswith("conftest.py"):
                continue

            yield from self.collected(
                tree.body,
                pytestmark(tree),
                self.chain(path),
                path,
                ()
            )


def quoted(dotted: str) -> Iterator[Binding]:
    """
    Yields the module the longest prefix of the quoted name `dotted` names,
    if any prefix names one.
    """
    for prefix in reversed([*prefixes(dotted)][1:]):
        if target := located(prefix):
            yield Binding(target, quoted=True)
            return


def walked(nodes: Iterable[AST]) -> Iterator[Binding]:
    """
    Yields each file under each package whose `__path__` the `nodes` of a
    module read, in code or in a quoted program, where they name a loader
    `LOADERS` matches, which imports a module by a name computed from that
    path.
    """
    bound, loads, read = {}, False, set()

    for node in nodes:
        match node:
            case Import() | ImportFrom(): bound.update(imported(node))
            case Constant(value=str(text)):
                loads |= bool(LOADERS.search(text))
                read.update(PATHS.findall(text))
            case Attribute(attr="__path__", value=value): read.add(unparse(value))
            case Name(id=name) | Attribute(attr=name):
                loads |= bool(LOADERS.fullmatch(name))

    for dotted in read if loads else ():
        first  = dotted.partition(".")[0]
        folder = source(bound.get(first, first) + dotted.removeprefix(first))

        yield from (Binding(path.as_posix()) for path in folder.rglob("*.py"))


if __name__ == "__main__":

    main(*argv[1:])
