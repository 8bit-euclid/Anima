from anima.animation.action import Enter, Exit, FCurvePreset
from anima.animation.reveal import Stagger
from anima.animation.scheduler import play
from anima.animation.stagger import by_key
from anima.latex.glyph_body import MeshQuality
from anima.latex.glyph_group import GlyphGroup
from anima.primitives.group import Group
from anima.primitives.lines import Segment


def test_latex_write_on():
    """Write on a line of text: each glyph's outline is traced, then its fill fades in."""
    group = GlyphGroup.from_tex_string("o08AaB", name="WriteOn", mesh_quality=MeshQuality.high())
    play(
        Enter(
            group,
            (1, 241),
            preset=FCurvePreset.EASE_IN_OUT,
        ),
        Exit(
            group,
            (361, 421),
            preset=FCurvePreset.EASE_IN_OUT,
        ),
    )


def test_curves_reveal():
    """Reveal plain curves with the same abstractions, from the middle outwards."""
    xs = {}
    bars = []
    for x in range(-5, 6):
        bar = Segment((x, -1), (x, 1), width=0.1)
        xs[id(bar)] = x
        bars.append(bar)
    group = Group(bars, name="Bars")
    group.location = (0, -10, 0)
    reveal = Stagger(group, lag_ratio=0.3, order=by_key(lambda bar: abs(xs[id(bar)])))
    play(Enter(group, (1, 181), reveal=reveal, preset=FCurvePreset.SINE_IN_OUT))
