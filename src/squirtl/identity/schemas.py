"""
Defines the records the site's visual identity is declared in, which the
`identity.toml` beside this module holds and `squirtl write docs` writes
out as the JSON the site's drawings read and the `@theme` block its Tailwind
sheet imports:

- `Declared`, the base every record here builds on
- `Color`, a named color and the luminance WCAG 2.2 measures it at, `Step`,
  one of Denim's lighter and darker steps and the share of black or white it
  mixes in, and `Swatch`, a color of the site's theme on each color scheme's
  ground
- `Face`, `Faces`, `Ramp`, `Hue`, `Scheme`, `Schemes`, `Lengths`, and
  `Motion`, the faces, the ramps of each hue, the colors each color
  scheme gives its roles, and the lengths and the timing every drawing shares
- `Glyph`, `Sprite`, `Badge`, `Letter`, `Letters`, `LogoBlock`, `Scene`, and
  `Logo`, the marks drawn from the display face's dots and from Pokémon
  Blue's pixels
- `ProjectMark`, an emoji opening a pull request's sections and the
  workflows' names
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
from typing       import Annotated, ClassVar, Literal, NamedTuple, Self
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
type Triple     = tuple[float, float, float]


class Oklab(NamedTuple):
    """
    The matrices Ottosson converts between linear sRGB and OKLab through,
    each a row per output.
    """

    lab: tuple[Triple, Triple, Triple]
    """
    From the cube roots of the cone responses to OKLab.
    """

    lms: tuple[Triple, Triple, Triple]
    """
    From linear sRGB to the cone responses.
    """

    lms_from_lab: tuple[Triple, Triple, Triple]
    """
    From OKLab back to the cube roots of the cone responses.
    """

    rgb_from_lms: tuple[Triple, Triple, Triple]
    """
    From the cone responses back to linear sRGB.
    """


OKLAB = Oklab(
    lab = (
        (0.2104542553, 0.7936177850, -0.0040720468),
        (1.9779984951, -2.4285922050, 0.4505937099),
        (0.0259040371, 0.7827717662, -0.8086757660)
    ),
    lms = (
        (0.4122214708, 0.5363325363, 0.0514459929),
        (0.2119034982, 0.6806995451, 0.1073969566),
        (0.0883024619, 0.2817188376, 0.6299787005)
    ),
    lms_from_lab = (
        (1, 0.3963377774, 0.2158037573),
        (1, -0.1055613458, -0.0638541728),
        (1, -0.0894841775, -1.2914855480)
    ),
    rgb_from_lms = (
        (4.0767416621, -3.3077115913, 0.2309699292),
        (-1.2684380046, 2.6097574011, -0.3413193965),
        (-0.0041960863, -0.7034186147, 1.7076147010)
    )
)


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

    purpose: str
    """
    What the site draws in the color.
    """

    @property
    def lab(self) -> tuple[float, float, float]:
        """
        Converts the color into OKLab, its lightness and its two opposing
        axes, through the matrices Ottosson defines it by.
        """
        cones = [sumprod(row, self.linear) ** (1 / 3) for row in OKLAB.lms]

        return tuple(sumprod(row, cones) for row in OKLAB.lab)

    @property
    def linear(self) -> tuple[float, float, float]:
        """
        Reads each of the color's channels as the linear light sRGB decodes
        it to, from 0 to 1.
        """
        return tuple(
            value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
            for value in (channel / 255 for channel in bytes.fromhex(self.hex[1:]))
        )

    @property
    def luminance(self) -> float:
        """
        Measures the color's relative luminance as WCAG 2.2 defines it, from
        0 for black to 1 for white.
        """
        return sumprod((0.2126, 0.7152, 0.0722), self.linear)

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

    def mix(self, share: float, toward: Color) -> Hex:
        """
        Mixes the color in OKLab the share `share` of the way toward
        `toward`, as `color-mix(in oklab, …)` mixes two colors, and encodes
        the mix back into sRGB, each channel clipped to its range.
        """
        lab = [mine + (theirs - mine) * share for mine, theirs in zip(
            self.lab,
            toward.lab
        )]
        cones   = [sumprod(row, lab) ** 3 for row in OKLAB.lms_from_lab]
        light   = (min(1, max(0, sumprod(row, cones))) for row in OKLAB.rgb_from_lms)
        encoded = (
            12.92 * value if value <= 0.0031308 else 1.055 * value ** (1 / 2.4) - 0.055
            for value in light
        )

        return "#" + bytes(round(255 * value) for value in encoded).hex()


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

    purpose: str
    """
    What the site sets in the face.
    """

    x_height: float
    """
    The height of the face's lowercase letters as a share of its em, the
    `sxHeight` its OS/2 table records, the body's at the optical size body
    text sets at.
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

    sizes: dict[str, float]
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

    travel: tuple[float, float, float, float]
    """
    The control points of the cubic Bézier a mark moving from one place to
    another eases along, slow at both ends.
    """

    @property
    def easing(self) -> str:
        """
        Writes the curve as a CSS `cubic-bezier()` function.
        """
        return self.bezier(self.curve)

    @property
    def traveling(self) -> str:
        """
        Writes the travel curve as a CSS `cubic-bezier()` function.
        """
        return self.bezier(self.travel)

    @staticmethod
    def bezier(points: tuple[float, float, float, float]) -> str:
        """
        Writes the control points of a cubic Bézier as a CSS
        `cubic-bezier()` function, each at its shortest.
        """
        return f"cubic-bezier({', '.join(f'{point:g}' for point in points)})"


class ProjectMark(Declared):
    """
    One project mark, the glyph opening a part of what the repository
    publishes, beside what it depicts and each place it opens.
    """

    depicts: str
    """
    What the glyph depicts from the world of Pokémon Blue and its console.
    """

    glyph: str
    """
    The emoji the mark is drawn as.
    """

    gate: bool = False
    """
    Whether the mark opens the name of the gate each workflow ends on.
    """

    section: str | None = None
    """
    The section of a pull request's body whose heading the mark opens, or
    `None` where it opens none.
    """

    workflows: bool = False
    """
    Whether the mark opens the name of every workflow.
    """


class Ramp(Declared):
    """
    The steps one hue takes on one color scheme's ground, each mixed in
    OKLab, the shades toward that ground, the deep step toward Mirage, the
    pale step toward Athens Gray, and the text step toward the other ground.
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

    ink: float = Field(default=0, ge=0, lt=1)
    """
    The share of the other color scheme's ground the text step mixes into
    the hue in OKLab, 0 where text in the hue takes the hue itself.
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


class Step(Color):
    """
    One of Denim's lighter and darker steps, beside the share of black or
    white it mixes into Denim in OKLab.
    """

    toward: Literal["black", "white"]
    """
    The color the step mixes Denim toward.
    """

    share: float = Field(gt=0, lt=1)
    """
    The share of `toward` the step mixes in.
    """

    @property
    def target(self) -> Color:
        """
        The black or the white the step mixes toward.
        """
        return Color(
            hex     = "#000000" if self.toward == "black" else "#ffffff",
            name    = self.toward,
            purpose = f"The {self.toward} a step mixes toward"
        )


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

    @property
    def code_size(self) -> float:
        """
        The size code sets at in ems of the text around it, the body's
        x-height over the code face's, so the lowercase letters of either
        stand at one height.
        """
        return self.body.x_height / self.code.x_height


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

    citation: dict[str, Swatch]
    """
    The colors a footnote's phone draws in, each under the name its
    `--color-citation-*` variable takes, which mark citations alone.
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

    project_marks: tuple[ProjectMark, ...]
    """
    The marks opening the sections of a pull request's body, the name of
    every workflow, and the gate each workflow ends on.
    """

    ramp: dict[str, Step]
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

    shares: tuple[float, float, float, float]
    """
    The share of the ground each of a hue's four shades mixes into the hue
    in OKLab, from nearest the ground to the fourth.
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
    def headings(self) -> dict[str, str]:
        """
        Maps each section of a pull request's body a project mark opens to
        the glyph of that mark.
        """
        return {mark.section: mark.glyph for mark in self.project_marks if mark.section}

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
            "ease-travel"   : self.motion.traveling,
            "text-code"     : f"{self.faces.code_size:.4g}em",
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
            {f"citation-{name}": swatch for name, swatch in self.citation.items()},
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

    @property
    def workflow_mark(self) -> str:
        """
        Names the glyph of the project mark opening every workflow's name.
        """
        return next(mark.glyph for mark in self.project_marks if mark.workflows)

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

    @model_validator(mode="after")
    def placed(self) -> Self:
        """
        Refuses project marks sharing a glyph, two marks opening one
        section, and other than one mark opening every workflow's name or
        the gate each workflow ends on.
        """
        marks  = self.project_marks
        places = (
            [mark.glyph for mark in marks],
            [mark.section for mark in marks if mark.section]
        )

        if any(len({*names}) < len(names) for names in places):
            raise ValueError("two project marks share a glyph or a section")
        if any(
            sum(getattr(mark, place) for mark in marks) != 1
            for place in ("gate", "workflows")
        ):
            raise ValueError(
                "other than one project mark opens the workflows' names or their gate"
            )

        return self

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
        an order and sections naming a hue other than once between them, a
        step, a shade, or a text step that is not the mix its share names,
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
        if any(
            step.hex != self.colors["primary"].mix(step.share, step.target)
            for step in self.ramp.values()
        ):
            raise ValueError("a step of Denim's ramp is not the mix it names")
        if any(
            shade != self.colors[hue.token].mix(share, self.palette[roles.ground])
            for hue in self.hues.values()
            for scheme, roles in self.schemes
            for shade, share in zip(getattr(hue, scheme).shades, self.shares)
        ):
            raise ValueError(
                "a hue's shade is not the mix of its ground `shares` names"
            )
        if any(
            ramp.text != (
                self.ramp[getattr(self.schemes, scheme).link].hex
                if hue.token == "primary"
                else self.colors[hue.token].mix(
                    ramp.ink,
                    self.palette[getattr(self.schemes, other).ground]
                )
            )
            for hue in self.hues.values()
            for scheme, other in (("light", "dark"), ("dark", "light"))
            for ramp in [getattr(hue, scheme)]
        ):
            raise ValueError("a hue's text step is not the mix its `ink` names")
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
