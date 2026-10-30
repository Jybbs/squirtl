"""
Pins what the identity's records declare and derive, covering:

- The contrast WCAG 2.2 measures between two colors, against the figures
  the identity's palette records, and the 4.5:1 each tone of body text
  holds on each surface in each scheme
- The color each hue marks in on each ground, the contrast each section's
  mark holds there, and the color each role takes on each scheme
- The four colors a section's badge draws its Game Boy shades in on each
  ground
- The `@theme` block the site's Tailwind sheet imports, a color the two
  schemes share written once, and the `cubic-bezier()` every transition
  eases along
- The faces' CSS stacks and the Google Fonts queries they load through
- The names a reference may not misspell, the keys a declaration may not
  leave out, and the names two theme colors may not share, each refused as
  the file is read
"""

from functools import reduce
from operator  import getitem
from pydantic  import ValidationError
from pytest    import fixture, mark, param, raises
from re        import escape
from tomllib   import loads

from squirtl.identity.schemas import Color, Face, Identity, Motion, Swatch


@fixture
def declared() -> dict:
    """
    Reads the identity `Identity.file` declares as the plain table its
    records validate, so a case changes one key before validating it.
    """
    return loads(Identity.file.read_text(encoding="utf-8"))


@mark.parametrize(
    ("ink", "ground", "ratio"),
    [
        param("primary", "ground", 4.36, id="denim-on-athens-gray"),
        param("mid", "dark", 6.13, id="denim-mid-on-mirage"),
        param("dark", "ground", 16.30, id="mirage-on-athens-gray"),
        param("quiet", "ground", 6.99, id="emperor-on-athens-gray"),
        param("muted", "dark", 6.29, id="mid-gray-on-mirage")
    ]
)
def test_contrast_matches_the_ratio_the_palette_records(
    ground : str,
    ink    : str,
    ratio  : float
):
    """
    Pins each contrast ratio the identity records for the palette to the
    ratio `Color.contrast` measures, to two places.
    """
    palette = Identity.read().palette

    assert round(palette[ink].contrast(palette[ground]), 2) == ratio


def test_a_badge_draws_in_its_hues_shades_on_each_ground():
    """
    Pins that a section's badge draws its four shades from its hue's
    lightest shade, third shade, mark, and text on the light ground, and
    from its second shade, third shade, mark, and pale step on the dark one.
    """
    identity = Identity.read()
    fern     = identity.hues["fern"]
    written  = fern.swatches(identity.marks["fern"])

    assert [written[f"badge-{shade}"] for shade in range(4)] == [
        Swatch(dark=fern.dark.shades[1], light=fern.light.shades[0]),
        Swatch(dark=fern.dark.shades[2], light=fern.light.shades[2]),
        identity.marks["fern"],
        Swatch(dark=fern.dark.pale, light=fern.light.text)
    ]


@mark.parametrize(
    ("hue", "light", "dark"),
    [
        param("amethyst", "#ba55d3", "#ba55d3", id="amethyst-marks-in-its-hue"),
        param(
            "cerulean",
            "#4d7288",
            "#91ddff",
            id = "cerulean-marks-in-its-text-on-light"
        ),
        param("denim", "#3d6fd0", "#3d6fd0", id="denim-marks-in-its-hue"),
        param("fern", "#3e7456", "#5cb878", id="fern-marks-in-its-ink-on-light"),
        param("forest", "#0e5900", "#658f60", id="forest-marks-in-its-text-on-dark"),
        param("heath", "#815e6e", "#c08597", id="heath-marks-in-its-ink-on-light"),
        param("indigo", "#5d05a4", "#9373c9", id="indigo-marks-in-its-text-on-dark"),
        param("seacaller", "#4b8488", "#4b8488", id="seacaller-marks-in-its-hue")
    ]
)
def test_marks_take_the_ink_step_only_under_three_to_one(
    dark  : str,
    hue   : str,
    light : str
):
    """
    Pins that a hue marks in itself where it holds 3:1 against the ground
    and in its text step where it does not, which leaves Heath, Fern, and
    Cerulean in their text steps on the light ground and Forest and Indigo
    in theirs on the dark.
    """
    assert Identity.read().marks[hue] == Swatch(dark=dark, light=light)


@mark.parametrize(
    ("section", "hue", "light", "dark"),
    [
        param("commands", "forest", 7.80, 4.82, id="commands"),
        param("methods", "indigo", 9.44, 4.73, id="methods"),
        param("results", "cerulean", 4.68, 11.94, id="results")
    ]
)
def test_each_section_marks_in_its_hue_at_the_contrast_the_identity_records(
    dark    : float,
    hue     : str,
    light   : float,
    section : str
):
    """
    Pins the hue each section takes and the contrast its mark holds against
    each ground to the ratios the identity records, each past the 4.5:1 WCAG
    2.2 sets for text.
    """
    identity = Identity.read()
    mark     = identity.marks[identity.sections[section]]
    palette  = identity.palette

    assert (
        identity.sections[section],
        round(Color(hex=mark.light, name="Mark").contrast(palette["ground"]), 2),
        round(Color(hex=mark.dark, name="Mark").contrast(palette["dark"]), 2)
    ) == (hue, light, dark)


def test_body_text_holds_four_and_a_half_to_one_on_every_surface():
    """
    Pins that each tone the site sets body text in reaches the 4.5:1 WCAG
    2.2 sets for body text on each surface a page lays text on, its ground
    and the lift a panel or a code block takes, in each color scheme.
    """
    identity = Identity.read()
    palette  = identity.palette

    assert [
        (scheme, text, surface)
        for scheme, roles in identity.schemes
        for text in ("hover", "ink", "link", "quiet")
        for surface in ("ground", "lift")
        if palette[getattr(roles, text)].contrast(
            palette[getattr(roles, surface)]
        ) < 4.5
    ] == []


def test_contrast_is_the_same_whichever_color_comes_first():
    """
    Asserts that the ratio between two colors reads the same from either
    side, the lighter color always on top of the fraction.
    """
    black, white = Color(hex="#000000", name="Black"), Color(
        hex  = "#ffffff",
        name = "White"
    )

    assert (black.contrast(white), white.contrast(black)) == (21.0, 21.0)


@mark.parametrize(
    ("swatch", "value"),
    [
        param(
            Swatch(dark="#121722", light="#f3f4f7"),
            "light-dark(#f3f4f7, #121722)",
            id = "differing"
        ),
        param(Swatch(dark="#3d6fd0", light="#3d6fd0"), "#3d6fd0", id="shared")
    ]
)
def test_a_swatch_writes_light_dark_only_where_the_schemes_differ(
    swatch : Swatch,
    value  : str
):
    """
    Asserts that a color the two schemes share is written once, whereas one
    that differs is written through `light-dark()`, light first.
    """
    assert swatch.value == value


def test_motion_writes_its_curve_as_a_css_function():
    """
    Asserts that the timing's curve reads as the `cubic-bezier()` a
    transition takes, each control point at its shortest.
    """
    assert Motion(
        curve    = (0.32, 0.72, 0.0, 1.0),
        duration = 150
    ).easing == "cubic-bezier(0.32, 0.72, 0, 1)"


def test_the_sheet_clears_tailwinds_theme_and_declares_each_value_in_order():
    """
    Pins that the `@theme` block opens on clearing Tailwind's own theme and
    declares every value once, in the order of their names, each length in
    rems from its pixels and each border in pixels.
    """
    lines = Identity.read().sheet.splitlines()
    names = [line.strip().partition(":")[0] for line in lines[2:-1]]

    assert lines[:2] == ["@theme static {", "  --*: initial;"]
    assert names == sorted(names)
    assert {
        "  --border-width-bar: 3px;", "  --spacing-4: 1rem;",
        "  --text-label: 0.6875rem;"
    } <= {*lines}


@mark.parametrize(
    ("face", "stack", "query"),
    [
        param(
            Face(
                axes     = "wght@400",
                fallback = ("ui-monospace", "Menlo", "monospace"),
                family   = "JetBrains Mono"
            ),
            "'JetBrains Mono', ui-monospace, 'Menlo', monospace",
            "JetBrains+Mono:wght@400",
            id = "code"
        ),
        param(
            Face(axes="ital@0;1", fallback=("Georgia", "serif"), family="Literata"),
            "'Literata', 'Georgia', serif",
            "Literata:ital@0;1",
            id = "body"
        )
    ]
)
def test_a_face_quotes_every_family_but_the_generic_ones(
    face  : Face,
    query : str,
    stack : str
):
    """
    Asserts that a face's stack quotes every family it names but a generic
    family, and that its query joins the family, its spaces as `+`, to its
    axes.
    """
    assert (face.stack, face.query) == (stack, query)


def test_the_shipped_declaration_holds_every_field_the_record_declares(declared: dict):
    """
    Asserts that `identity.toml` declares a key for every field `Identity`
    reads and no other, so no field falls back on a default the file never
    states.
    """
    assert {*declared} == {*Identity.model_fields}


@mark.parametrize(
    ("path", "value", "message"),
    [
        param(
            ("schemes", "light", "ink"),
            "ink-black",
            "names no color or hue: ink-black",
            id = "scheme"
        ),
        param(("roles", "agent"), "teal", "names no color or hue: teal", id="role"),
        param(
            ("logo", "light", "ahead"),
            "paler",
            "names no color or hue: paler",
            id = "logo"
        ),
        param(
            ("hues", "fern", "token"),
            "accent-9",
            "names no color or hue: accent-9",
            id = "hue"
        ),
        param(
            ("order",),
            ("denim",),
            "the order and the sections name each hue other than once",
            id = "order"
        ),
        param(
            ("sections", "methods"),
            "fern",
            "the order and the sections name each hue other than once",
            id = "section-takes-a-series-hue"
        ),
        param(
            ("sections", "methods"),
            "violet",
            "names no color or hue: violet",
            id = "section"
        ),
        param(
            ("logo", "letters", "R", "frame"),
            6,
            "a letter names a frame Blue's sprite",
            id = "frame"
        ),
        param(("sprites",), {}, "the sprites leave out `player`", id="sprite")
    ]
)
def test_a_misspelled_reference_fails_the_read(
    declared : dict,
    message  : str,
    path     : tuple[str, ...],
    value    : object
):
    """
    Pins that a reference naming no color, no hue, or no frame of Blue's
    sprite, an order and sections leaving out a hue or sharing one, and
    sprites leaving out Blue's each fail validation, naming what they miss.
    """
    *parents, key = path
    reduce(getitem, parents, declared)[key] = value

    with raises(ValidationError, match=message):
        Identity.model_validate(declared)


@mark.parametrize(
    "path",
    [
        param(("faces", "code"), id="face"),
        param(("logo", "letters", "R"), id="letter"),
        param(("schemes", "dark"), id="scheme")
    ]
)
def test_a_declaration_leaving_out_a_key_fails_the_read(
    declared : dict,
    path     : tuple[str, ...]
):
    """
    Pins that a declaration leaving out a face, one of the logo's letters,
    or a color scheme fails validation on the key it leaves out, rather than
    passing until a later read of that key fails.
    """
    *parents, key = path
    del reduce(getitem, parents, declared)[key]

    with raises(ValidationError, match=rf"{escape('.'.join(path))}\n  Field required"):
        Identity.model_validate(declared)


def test_tones_read_each_role_from_the_name_its_scheme_gives():
    """
    Pins the color each role takes on each scheme to the color the scheme's
    name for it reads.
    """
    tones = Identity.read().tones

    assert (
        tones["light"]["ground"],
        tones["dark"]["ground"],
        tones["light"]["link"]
    ) == (
        "#f3f4f7", "#121722", "#294e95"
    )


def test_two_theme_colors_sharing_a_name_fail_the_read(declared: dict):
    """
    Pins that a role named as one of the logo's colors fails validation,
    naming the variable both would write, rather than one color of the
    site's theme silently replacing the other.
    """
    declared["roles"]["ahead"] = "fern"

    with raises(ValidationError, match="two theme colors share a name: ahead"):
        Identity.model_validate(declared)
