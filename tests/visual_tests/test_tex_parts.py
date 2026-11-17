"""Visual gallery for semantic TeX parts.

Run from the repository root using the default scene in ``anima.main``:

    make run

Or render a still:

    make render-frame FRAME=1 PREVIEW=1
"""

from anima.latex.glyph_group import GlyphGroup
from anima.latex.tex_document import TeXDocument


def _label(text: str, x: float, y: float, *, font_size: float = 12) -> GlyphGroup:
    group = GlyphGroup.from_tex_string(text, font_size=font_size)
    group.location = (x, y, 0)
    group.set_palette_color("byrne_euclid", "black")
    return group


def _color_part(group: GlyphGroup, name: str, color: str) -> None:
    for glyph in group.part(name):
        glyph.set_palette_color("byrne_euclid", color)


def test_semantic_parts() -> None:
    """Build a gallery of named selections, shapes, empty parts, and kerning."""
    _label(r"Semantic \TeX{} Parts", -8.5, 4.2, font_size=20)
    _label("Each selected part is colored independently", -8.5, 3.45)

    _label("Repeated", -8.5, 2.35)
    repeated = GlyphGroup.from_tex_parts(
        {"first": r"$a", "plus": "+", "second": "a", "equals": "=", "third": r"2a$"},
        name="RepeatedParts",
        font_size=22,
    )
    repeated.location = (-3.5, 2.35, 0)
    repeated.set_palette_color("byrne_euclid", "black")
    for name, color in (("first", "red1"), ("second", "blue1"), ("third", "yellow1")):
        _color_part(repeated, name, color)

    _label("Macro + rule", -8.5, 0.65)
    template = TeXDocument().set_defaults().add_new_command("demoFrac", r"\frac{#1}{#2}")
    fraction = GlyphGroup.from_tex_parts(
        {"fraction": r"$\demoFrac{x^2-1}{x+1}", "equals": "=", "result": r"x-1$"},
        name="FractionParts",
        font_size=22,
        tex_template=template,
    )
    fraction.location = (-3.5, 0.65, 0)
    fraction.set_palette_color("byrne_euclid", "black")
    _color_part(fraction, "fraction", "red1")
    _color_part(fraction, "result", "blue1")

    _label("Sum + gap", -8.5, -1.05)
    summation = GlyphGroup.from_tex_parts(
        {"sum": r"$\sum_{i=1}^{n} x_i", "gap": r"\qquad ", "equals": "=", "rhs": r"\frac{n(n+1)}{2}$"},
        name="SummationParts",
        font_size=22,
    )
    summation.location = (-3.5, -1.05, 0)
    summation.set_palette_color("byrne_euclid", "black")
    _color_part(summation, "sum", "blue1")
    _color_part(summation, "rhs", "red1")
    assert len(summation.part("gap")) == 0

    _label("Empty part", -8.5, -2.75)
    spaced = GlyphGroup.from_tex_parts(
        {"first": "A", "gap": r"\hspace{1.5em}", "second": "V"}, name="EmptyPart", font_size=22
    )
    spaced.location = (-3.5, -2.75, 0)
    _color_part(spaced, "first", "red1")
    _color_part(spaced, "second", "blue1")
    assert len(spaced.part("gap")) == 0
    _label("(gap has no glyphs)", 0.5, -2.75)

    _label("Kerning", -8.5, -4.15)
    _label("Parts:", -3.5, -4.15)
    marked = GlyphGroup.from_tex_parts({"first": "A", "second": "V"}, name="MarkedAV", font_size=22)
    marked.location = (-1.5, -4.15, 0)
    _color_part(marked, "first", "red1")
    _color_part(marked, "second", "blue1")
    _label("Plain:", 1.0, -4.15)
    plain = GlyphGroup.from_tex_string("AV", name="PlainAV", font_size=22)
    plain.location = (2.9, -4.15, 0)
    plain.set_palette_color("byrne_euclid", "black")
