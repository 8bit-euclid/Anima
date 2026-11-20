"""Visual gallery for semantic TeX parts.

Run from the repository root using the default scene in ``anima.main``:

    make run

Or render stills at the start, middle, and end of the reveal (at the default 60 fps):

    make render-frame FRAME=1 PREVIEW=1
    make render-frame FRAME=121 PREVIEW=1
    make render-frame FRAME=241 PREVIEW=1
"""

from anima.animation.action import Enter, FCurvePreset
from anima.animation.effects import Fade, Stagger
from anima.animation.scheduler import Scheduler
from anima.latex.glyph_group import GlyphGroup
from anima.latex.tex_document import TeXDocument
from anima.layout import Layout
from anima.materials.material import get_palette_color


def _label(text: str, *, font_size: float = 12) -> GlyphGroup:
    group = GlyphGroup.from_tex_string(text, font_size=font_size)
    group.set_palette_color("byrne_euclid", "black")
    return group


def _color_part(group: GlyphGroup, name: str, color: str) -> None:
    group.part(name).set_color(get_palette_color("byrne_euclid", color))


def test_semantic_parts() -> None:
    """Build a gallery of styled and animated selections, shapes, and kerning."""
    title = _label(r"Semantic \TeX{} Parts", font_size=20)
    subtitle = _label("Each selected part is colored independently")

    repeated_label = _label("Repeated")
    repeated = GlyphGroup.from_tex_parts(
        {"first": r"$a", "plus": "+", "second": "a", "equals": "=", "third": r"2a$"},
        name="RepeatedParts",
        font_size=22,
    )
    repeated.set_palette_color("byrne_euclid", "black")
    for name, color in (("first", "red1"), ("second", "blue1"), ("third", "yellow1")):
        _color_part(repeated, name, color)

    fraction_label = _label("Macro + reveal")
    template = TeXDocument().set_defaults().add_new_command("demoFrac", r"\frac{#1}{#2}")
    fraction = GlyphGroup.from_tex_parts(
        {"fraction": r"$\demoFrac{x^2-1}{x+1}", "equals": "=", "result": r"x-1$"},
        name="FractionParts",
        font_size=22,
        tex_template=template,
    )
    fraction.set_palette_color("byrne_euclid", "black")
    _color_part(fraction, "fraction", "red1")
    _color_part(fraction, "result", "blue1")

    summation_label = _label("Sum + gap")
    summation = GlyphGroup.from_tex_parts(
        {"sum": r"$\sum_{i=1}^{n} x_i", "gap": r"\qquad ", "equals": "=", "rhs": r"\frac{n(n+1)}{2}$"},
        name="SummationParts",
        font_size=22,
    )
    summation.set_palette_color("byrne_euclid", "black")
    _color_part(summation, "sum", "blue1")
    _color_part(summation, "rhs", "red1")
    assert len(summation.part("gap")) == 0

    spaced_label = _label("Empty + opacity")
    spaced = GlyphGroup.from_tex_parts(
        {"first": "A", "gap": r"\hspace{1.5em}", "second": "A"}, name="EmptyPart", font_size=22
    )
    _color_part(spaced, "first", "blue1")
    spaced.part("second").set_color(get_palette_color("byrne_euclid", "blue1")).set_opacity(0.35)
    assert len(spaced.part("gap")) == 0
    spaced_description = _label("(empty gap; 100\\% / 35\\%)")

    kerning_label = _label("Kerning")
    parts_label = _label("Parts:")
    marked = GlyphGroup.from_tex_parts({"first": "A", "second": "V"}, name="MarkedAV", font_size=22)
    _color_part(marked, "first", "red1")
    _color_part(marked, "second", "blue1")
    plain_label = _label("Plain:")
    plain = GlyphGroup.from_tex_string("AV", name="PlainAV", font_size=22)
    plain.set_palette_color("byrne_euclid", "black")

    opacity_row = Layout([spaced, spaced_description]).tile(direction="right", gap=0.6)
    kerning_row = Layout([parts_label, marked, plain_label, plain]).tile(direction="right", gap=0.5)
    rows = Layout.grid(
        [
            [repeated_label, repeated],
            [fraction_label, fraction],
            [summation_label, summation],
            [spaced_label, opacity_row],
            [kerning_label, kerning_row],
        ],
        column_gap=0.8,
        row_gap=0.5,
    )
    Layout([title, subtitle, rows]).tile(gap=0.55).place_in_safe_area()

    reveal = Stagger(fraction, children=fraction.part("fraction"), lag_ratio=0.5, child_effect=Fade)
    Scheduler().add_action(Enter(reveal, 4, preset=FCurvePreset.LINEAR), with_previous=True)
