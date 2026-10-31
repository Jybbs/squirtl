"""
Defines the records the site's visual identity is declared in, which the
`identity.toml` beside this module holds and `squirtl write docs` writes
out as the JSON the site's drawings read and the `@theme` block its Tailwind
sheet imports:

- `Declared`, the base every record here builds on
- `Color`, a named color and the luminance WCAG 2.2 measures it at, and
  `Swatch`, a color of the site's theme on each color scheme's ground
- `Face`, `Faces`, `Ramp`, `Hue`, `Scheme`, `Schemes`, `Lengths`, and
  `Motion`, the faces, the ramps of each hue, the colors each color
  scheme gives its roles, and the lengths and the timing every drawing shares
- `Glyph`, `Sprite`, `Badge`, `Letter`, `Letters`, `LogoBlock`, `Scene`, and
  `Logo`, the marks drawn from the display face's dots and from Pokémon
  Blue's pixels
- `Identity`, the whole declaration
"""

from collections             import Counter
from functools               import reduce
from importlib.resources     import files
from importlib.resources.abc import Traversable
from itertools               import chain
from math         import sumprod
from operator     import or_
from pydantic     import BaseModel, BeforeValidator, Field, StringConstraints, computed_field, model_validator
from tomllib      import loads
from typing       import Annotated, ClassVar, Literal, Self
from urllib.parse import quote_plus

type Cell = tuple[int, int]
type Grid = Annotated[
    tuple[Row, ...],
    BeforeValidator(
        lambda grid: tuple(grid.split()) if isinstance(grid, str) else grid
    ),
    Field(max_length=16, min_length=16)
]
type Hex        = Annotated[str, StringConstraints(pattern=r"^#[0-9a-f]{6}$")]
type Row        = Annotated[str, StringConstraints(pattern=r"^[0-3]{16}$")]
type SchemeName = Literal["dark", "light"]


class Declared(BaseModel, extra="forbid", frozen=True, use_attribute_docstrings=True):
    """
    The base of every record the identity declares, which refuses a key no
    field declares and an assignment once built, and takes the docstring
    beneath each field as that field's description.
    """


class Badge(Declared):
    """
    One of the gym badges a section of the site carries as its mark, drawn
    from its Pokémon Blue sprite.
    """

    grid: Grid
    """
    The badge's 16 rows of 16 pixels, each the Game Boy shade from 0, the
    lightest, to 3, the darkest.
    """

    name: str
    """
    The badge's name, as the game gives it.
    """


class Color(Declared):
    """
    A color the identity names, beside the luminance WCAG 2.2 measures it
    at.
    """

    hex: Hex
    """
    The color as six lowercase hex digits after a `#`.
    """

    name: str
    """
    The color's name, as the identity records it.
    """

    @property
    def luminance(self) -> float:
        """
        Measures the color's relative luminance as WCAG 2.2 defines it, from
        0 for black to 1 for white.
        """
        return sumprod(
            (0.2126, 0.7152, 0.0722),
            (
                value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
                for value in (channel / 255 for channel in bytes.fromhex(self.hex[1:]))
            )
        )

    @property
    def swatch(self) -> Swatch:
        """
        Pairs the color with itself on both grounds, as the swatch of a
        color the two color schemes share.
        """
        return Swatch(dark=self.hex, light=self.hex)

    def contrast(self, other: Color) -> float:
        """
        Measures the contrast ratio WCAG 2.2 defines between this color and
        `other`, from 1 for two equal colors to 21 for black on white.
        """
        lighter, darker = sorted((self.luminance, other.luminance), reverse=True)

        return (lighter + 0.05) / (darker + 0.05)


class Face(Declared):
    """
    One of the faces the site sets its text in, loaded through Google Fonts.
    """

    axes: str
    """
    The axes and the values the site loads the face at, written as the
    Google Fonts CSS API takes them after the family's name and a `:`.
    """

    fallback: tuple[str, ...]
    """
    The families a browser sets the text in until the face loads, in the
    order it tries them.
    """

    family: str
    """
    The family's name, as Google Fonts lists it.
    """

    @computed_field
    @property
    def query(self) -> str:
        """
        The `family` parameter the Google Fonts CSS API reads the face from.
        """
        return f"{quote_plus(self.family)}:{self.axes}"

    @computed_field
    @property
    def stack(self) -> str:
        """
        The value of a `font-family` declaration setting text in the face.
        """
        return ", ".join(
            name if name.endswith(("monospace", "serif")) else f"'{name}'"
            for name in (self.family, *self.fallback)
        )


class Glyph(Declared):
    """
    One character of the display face as the dots it lights on its grid of
    cells, each cell one round dot of the face's settings.
    """

    advance: int
    """
    The cells the character spans, the space after it included.
    """

    cells: Annotated[str, StringConstraints(pattern=r"^([0-9a-f]{2})*$")]
    """
    The cells the character lights, each a pair of hex digits naming its
    column from the left and its row up from the baseline, each raised by
    five so a cell below the baseline stays one digit.
    """


class Lengths(Declared):
    """
    The lengths every drawing and every utility of the site's theme share,
    in CSS pixels unless a field says otherwise.
    """

    borders: dict[str, int]
    """
    The widths of a border or a rule, each under the name its utility takes.
    """

    breakpoints: dict[str, int]
    """
    The widths VitePress's default theme rearranges a page at, each under the
    prefix its responsive utilities take, which a container query reads as
    well so a widget rearranges at the same widths.
    """

    leading: dict[str, float]
    """
    The line heights, each a multiple of the type size under the name its
    utility takes.
    """

    plate: int
    """
    The width of the `viewBox` a single-panel chart is drawn in, the docs
    column's width at its widest.
    """

    radii: dict[str, int]
    """
    The corner radii, each under the step its utility names.
    """

    sizes: dict[str, int]
    """
    The fixed sizes the settled widgets set a part at, such as the slot a
    chip's mark sits in, each under the name its spacing utility takes.
    """

    spacing: dict[str, int]
    """
    The gaps and paddings, each under the step its utility names.
    """

    strokes: dict[str, float]
    """
    The stroke width of each kind of line a drawing draws.
    """

    text: dict[str, int]
    """
    The type scale, each size under the role it sets.
    """

    track: float
    """
    The letter spacing of text set in capitals, in ems.
    """

    weights: dict[str, int]
    """
    The weights text is set at, each under the name its utility takes.
    """


class Letter(Declared):
    """
    How the logo draws one of its two letters holding Blue, the R or the L.
    """

    block: Cell
    """
    The column and the row of the lower-left cell of the 2 by 2 block of
    cells Blue's square covers.
    """

    frame: int
    """
    The frame of Blue's sprite his square holds.
    """

    mirror: bool
    """
    Whether his frame is mirrored to face right.
    """

    route: tuple[Cell, ...]
    """
    The letter's dots in the order Blue passed them, each as its column and
    its row counted up from the foot.
    """


class LogoBlock(Declared):
    """
    The square holding Blue in the logo, in the 100 units of one cell.
    """

    outset: int
    """
    How far the square's edge sits outside the 2 by 2 cells it covers.
    """

    radius: int
    """
    The radius of the square's corners.
    """

    size: int
    """
    The square's side.
    """


class Motion(Declared):
    """
    The timing every transition on the site reads.
    """

    curve: tuple[float, float, float, float]
    """
    The control points of the cubic Bézier every transition eases along.
    """

    duration: int
    """
    The length of a transition, in milliseconds.
    """

    @property
    def easing(self) -> str:
        """
        Writes the curve as a CSS `cubic-bezier()` function.
        """
        return f"cubic-bezier({', '.join(f'{point:g}' for point in self.curve)})"


class Ramp(Declared):
    """
    The steps one hue takes on one color scheme's ground, each mixed in
    OKLab toward that ground.
    """

    deep: Hex
    """
    The hue at its deepest, for a fill that holds text in the ground's color.
    """

    pale: Hex
    """
    The hue at its palest, for a fill that holds text in the ink.
    """

    shades: tuple[Hex, Hex, Hex, Hex]
    """
    The four shades from nearest the ground, a chip's ground, to the fourth.
    """

    text: Hex
    """
    The step text in the hue takes on this ground, which holds 4.5:1 on the
    first shade.
    """


class Scene(Declared):
    """
    The colors the logo draws its trail and Blue's block in on one color
    scheme's ground, each named as the identity's colors name it.
    """

    ahead: str
    """
    The dot between Blue and the Poké Ball, the ground not yet covered.
    """

    block: str
    """
    Blue's square, which shows where his sprite leaves a pixel blank.
    """

    thirds: tuple[str, str, str]
    """
    The trail's oldest third, its middle third, and its newest third.
    """


class Scheme(Declared):
    """
    The color each role takes on one color scheme, each named as the
    identity's colors name it.
    """

    ground: str
    """
    The ground every page sits on.
    """

    hover: str
    """
    A link under the pointer.
    """

    ink: str
    """
    Body text.
    """

    lift: str
    """
    A surface raised above the ground.
    """

    link: str
    """
    A link at rest.
    """

    quiet: str
    """
    Quiet text, and the gray of a figure belonging to no role.
    """

    rule: str
    """
    A rule or a border between two parts of a page.
    """


class Sprite(Declared):
    """
    One actor or item of Pokémon Blue as the frames its sprite draws.
    """

    frames: tuple[Grid, ...]
    """
    Each frame's 16 rows of 16 pixels, each the Game Boy shade from 0, the
    lightest, to 3, the darkest.
    """


class Swatch(Declared):
    """
    A color the site's theme declares, beside the color it takes on each
    color scheme's ground.
    """

    dark: Hex
    """
    The color on the dark ground.
    """

    light: Hex
    """
    The color on the light ground.
    """

    @property
    def value(self) -> str:
        """
        Writes the color as a CSS value that follows the page's color
        scheme, through `light-dark()` where the two grounds take different
        colors.
        """
        light, dark = self.light, self.dark

        return dark if light == dark else f"light-dark({light}, {dark})"


class Faces(Declared):
    """
    The faces the site sets its text in, each under the role it sets.
    """

    body: Face
    """
    The face of body text.
    """

    code: Face
    """
    The face of code.
    """

    display: Face
    """
    The face of display text, whose dots the logo is set in.
    """


class Hue(Declared):
    """
    One hue, a series hue or a section's, and the ramp it takes on each
    color scheme.
    """

    dark: Ramp
    """
    The ramp on the dark ground.
    """

    light: Ramp
    """
    The ramp on the light ground.
    """

    token: str
    """
    The name of the hue's own color among the identity's colors.
    """

    def swatches(self, mark: Swatch) -> dict[str, Swatch]:
        """
        Pairs each step's color on the light ground with its color on the
        dark one, under the step's name:

        - `1` to `4`, the four shades
        - `deep`, `pale`, and `text`, the steps of those names
        - `mark`, the color `mark` gives the hue on each ground
        - `badge-0` to `badge-3`, the four colors a section's badge draws its
          Game Boy shades in, from the lightest to the darkest on the light
          ground and the dimmest to the brightest on the dark one
        """
        light, dark = self.light, self.dark

        return {
            **{
                str(step): Swatch(dark=on_dark, light=on_light)
                for step, (on_light, on_dark) in enumerate(
                    zip(light.shades, dark.shades),
                    start = 1
                )
            },
            "badge-0" : Swatch(dark=dark.shades[1], light=light.shades[0]),
            "badge-1" : Swatch(dark=dark.shades[2], light=light.shades[2]),
            "badge-2" : mark,
            "badge-3" : Swatch(dark=dark.pale, light=light.text),
            "deep"    : Swatch(dark=dark.deep, light=light.deep),
            "mark"    : mark,
            "pale"    : Swatch(dark=dark.pale, light=light.pale),
            "text"    : Swatch(dark=dark.text, light=light.text)
        }


class Letters(Declared):
    """
    How the logo draws each of its two letters holding Blue.
    """

    L: Letter
    """
    The L, whose last dot the Poké Ball is centered on.
    """

    R: Letter
    """
    The R.
    """


class Schemes(Declared):
    """
    The color each role takes on each color scheme.
    """

    dark: Scheme
    """
    The roles on the dark ground.
    """

    light: Scheme
    """
    The roles on the light ground.
    """


class Logo(Declared):
    """
    The logo, the name set in the display face's dots with the R and the L
    holding Blue and a Poké Ball ending the path he walks, in the 100 units
    of one cell.
    """

    ball: int
    """
    The side of the Poké Ball's sprite, centered on the L's last dot.
    """

    block: LogoBlock
    """
    The square each of Blue's frames sits in.
    """

    dark: Scene
    """
    The trail and the block on the dark ground.
    """

    letters: Letters
    """
    How the logo draws the R and the L.
    """

    light: Scene
    """
    The trail and the block on the light ground.
    """

    shades: tuple[str, str, str, str]
    """
    The color each Game Boy shade of a sprite takes, from the lightest to the
    darkest, where the lightest fills only the pixels the sprite encloses.
    """

    sprite: int
    """
    The side of Blue's sprite inside his square.
    """

    @property
    def named(self) -> dict[str, tuple[str, str]]:
        """
        Pairs each color the scenes name, under its name in the site's
        theme, with the name of the color it takes on the light ground and
        on the dark one.
        """
        light, dark = self.light, self.dark

        return {
            "ahead" : (light.ahead, dark.ahead),
            "block" : (light.block, dark.block),
            **{
                f"trail-{third}": names
                for third, names in enumerate(zip(light.thirds, dark.thirds), start=1)
            }
        }


class Identity(Declared):
    """
    The site's visual identity, its faces, palette, lengths, timing, and
    marks, as `file` declares it.
    """

    file: ClassVar[Traversable] = files(__package__) / "identity.toml"

    badges: tuple[Badge, ...]
    """
    The gym badges in the order the game awards them.
    """

    colors: dict[str, Color]
    """
    The palette's colors, each under its token.
    """

    faces: Faces
    """
    The faces, each under the role it sets.
    """

    glyphs: dict[str, Glyph]
    """
    The display face's characters as the dots each lights.
    """

    hues: dict[str, Hue]
    """
    The series hues and the sections' hues, each under its name.
    """

    lengths: Lengths
    """
    The lengths every drawing shares.
    """

    logo: Logo
    """
    The logo.
    """

    motion: Motion
    """
    The timing every transition reads.
    """

    name: str
    """
    The project's name as the logo and the site's title set it.
    """

    neutrals: dict[str, Color]
    """
    The grounds, the inks, and the rules, each under its token.
    """

    order: tuple[str, ...]
    """
    The series hues in the order a chart takes them, which leaves out every
    hue a section takes.
    """

    ramp: dict[str, Color]
    """
    Denim's lighter and darker steps, each under its name.
    """

    roles: dict[str, str]
    """
    The hue each role takes wherever it is drawn.
    """

    schemes: Schemes
    """
    The color each role takes on each color scheme.
    """

    sections: dict[str, str]
    """
    The hue each section of the site takes for its badge, its card, and its
    pages, under the folder the section opens on.
    """

    sprites: dict[str, Sprite]
    """
    The actors and the items of Pokémon Blue the site draws, each under its
    name.
    """

    tagline: str
    """
    The one sentence the front page and the site's card set beneath the name.
    """

    @property
    def palette(self) -> dict[str, Color]:
        """
        Gathers every color the identity names under the token a role or a
        mark refers to it by.
        """
        return self.colors | self.neutrals | self.ramp

    @property
    def sheet(self) -> str:
        """
        Writes the `@theme` block the site's Tailwind sheet builds its
        utilities from. The block clears Tailwind's own theme, then declares
        each color, face, weight, line height, length, duration, and easing
        curve the identity gives in the order of their names, writing a
        color that differs between the color schemes through `light-dark()`.
        """
        lengths = self.lengths
        sized   = {
            "breakpoint" : lengths.breakpoints,
            "container"  : lengths.breakpoints,
            "radius"     : lengths.radii,
            "spacing"    : lengths.spacing | lengths.sizes,
            "text"       : lengths.text
        }
        values = {
            **{f"color-{name}": swatch.value for name, swatch in self.swatches.items()},
            **{
                f"{kind}-{name}": f"{pixels / 16:g}rem"
                for kind, sizes in sized.items()
                for name, pixels in sizes.items()
            },
            **{f"border-width-{key}": f"{px}px" for key, px in lengths.borders.items()},
            **{f"font-{role}": face.stack for role, face in self.faces},
            **{
                f"font-weight-{key}": str(weight)
                for key, weight in lengths.weights.items()
            },
            **{
                f"leading-{key}": f"{height:g}"
                for key, height in lengths.leading.items()
            },
            "default-transition-duration"        : f"{self.motion.duration}ms",
            "default-transition-timing-function" : self.motion.easing,
            "ease-glide"    : self.motion.easing,
            "tracking-caps" : f"{lengths.track:g}em"
        }

        return "".join(
            [
                "@theme static {\n  --*: initial;\n",
                *(f"  --{name}: {value};\n" for name, value in sorted(values.items())),
                "}\n"
            ]
        )

    @property
    def swatches(self) -> dict[str, Swatch]:
        """
        Pairs the color each `--color-*` variable of the site's theme takes
        on the light ground with its color on the dark one, under the name
        that follows the prefix, alike on both for a color the schemes
        share.

        Raises:
            ValueError: Where two of the variables take one name.
        """
        marks   = self.marks
        palette = self.palette
        tones   = self.tones
        groups  = (
            {
                token: Swatch(dark=palette[on_dark].hex, light=palette[on_light].hex)
                for token, (on_light, on_dark) in self.logo.named.items()
            },
            {token: color.swatch for token, color in self.colors.items()},
            {
                color.name.lower().replace(" ", "-"): color.swatch
                for color in self.neutrals.values()
            },
            {
                role: Swatch(dark=tones["dark"][role], light=on_light)
                for role, on_light in tones["light"].items()
            },
            {
                f"{name}-{step}": swatch
                for name, hue in self.hues.items()
                for step, swatch in hue.swatches(marks[name]).items()
            },
            {role: marks[hue] for role, hue in self.roles.items()}
        )
        named = Counter(chain.from_iterable(groups))

        if shared := sorted(name for name, count in named.items() if count > 1):
            raise ValueError(f"two theme colors share a name: {', '.join(shared)}")

        return reduce(or_, groups)

    @computed_field
    @property
    def marks(self) -> dict[str, Swatch]:
        """
        The color each hue marks a chip's rule or a swatch in on each color
        scheme, the hue itself where it holds the 3:1 WCAG 2.2 sets for a
        graphical object against the ground, and its text step otherwise.
        """
        grounds = {scheme: self.palette[roles.ground] for scheme, roles in self.schemes}

        return {
            name: Swatch(
                **{
                    scheme: (
                        hue_color.hex
                        if hue_color.contrast(ground) >= 3
                        else getattr(hue, scheme).text
                    )
                    for scheme, ground in grounds.items()
                }
            )
            for name, hue in self.hues.items()
            for hue_color in [self.colors[hue.token]]
        }

    @classmethod
    def read(cls) -> Self:
        """
        Reads the identity `file` declares.
        """
        return cls.model_validate(loads(cls.file.read_text(encoding="utf-8")))

    @model_validator(mode="after")
    def refers(self) -> Self:
        """
        Refuses a name that names no color, no hue, or no sprite frame,
        an order and sections naming a hue other than once between them,
        sprites leaving out Blue's, and two colors of the site's theme under
        one name, so a misspelled reference fails the read rather than the
        site's build.
        """
        colors = {
            *(name for _, scheme in self.schemes for _, name in scheme),
            *chain.from_iterable(self.logo.named.values()),
            *self.logo.shades
        }
        missing = (
            colors - self.palette.keys()
            | {hue.token for hue in self.hues.values()} - self.colors.keys()
            | {*self.roles.values(), *self.sections.values()} - self.hues.keys()
        )

        if missing:
            raise ValueError(f"names no color or hue: {', '.join(sorted(missing))}")
        if sorted([*self.order, *self.sections.values()]) != sorted(self.hues):
            raise ValueError("the order and the sections name each hue other than once")
        if "player" not in self.sprites:
            raise ValueError("the sprites leave out `player`, Blue's")
        if any(
            letter.frame >= len(self.sprites["player"].frames)
            for _, letter in self.logo.letters
        ):
            raise ValueError("a letter names a frame Blue's sprite does not draw")

        self.swatches

        return self

    @computed_field
    @property
    def tones(self) -> dict[SchemeName, dict[str, Hex]]:
        """
        The color each role takes on each color scheme, read from the names
        `schemes` gives.
        """
        return {
            scheme: {role: self.palette[name].hex for role, name in roles}
            for scheme, roles in self.schemes
        }
