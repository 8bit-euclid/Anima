from datetime import timedelta

from anima.animation.action import Enter, Exit, FCurvePreset
from anima.animation.effects import Draw, Fade, Phase, Stagger
from anima.animation.scheduler import Scheduler
from anima.animation.stagger import by_key
from anima.latex.glyph import glyph_write_on
from anima.latex.glyph_body import MeshQuality
from anima.latex.glyph_group import GlyphGroup
from anima.primitives.group import Group
from anima.primitives.lines import Segment


def test_latex_write_on(duration: timedelta):
    """Write on a line of text: each glyph's outline is traced, then its fill fades in; then it exits.

    Schedules at the scheduler's cursor, so it runs after anything already scheduled.
    """
    group = GlyphGroup.from_tex_string("o08AaB", name="WriteOn", mesh_quality=MeshQuality.high())
    effect = Stagger(group, child_effect=glyph_write_on)
    scheduler = Scheduler()
    scheduler.add_action(Enter(effect, duration / 2, preset=FCurvePreset.EASE_IN_OUT))
    scheduler.wait(duration / 8)
    scheduler.add_action(
        Exit(Stagger(group, child_effect=glyph_write_on), duration * 3 / 8, preset=FCurvePreset.EASE_IN_OUT)
    )


def test_curves_reveal(duration: timedelta):
    """Reveal plain curves with the same abstractions, from the middle outwards.

    Returns:
        The unplaced action, so the caller chooses when it runs.
    """
    xs = {}
    bars = []
    for x in range(-5, 6):
        bar = Segment((x, -1), (x, 1), width=0.1)
        xs[id(bar)] = x
        bars.append(bar)
    group = Group(bars, name="Bars")
    group.location = (0, -10, 0)
    effect = Stagger(group, lag_ratio=0.3, order=by_key(lambda bar: abs(xs[id(bar)])), child_effect=Draw)

    sched = Scheduler()
    sched.add_action(Enter(effect, duration, preset=FCurvePreset.SINE_IN_OUT), with_previous=True)
