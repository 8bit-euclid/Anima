"""Tests for composable progress effects."""

from datetime import timedelta

import pytest
from mathutils import Matrix, Vector

from anima.animation.effects import Callback, Draw, Effect, Fade, Phase, Scale, Stagger, Together
from anima.animation.stagger import reversed_order
from anima.latex.glyph import Glyph, glyph_write_on
from anima.latex.glyph_group import GlyphGroup
from anima.primitives.chains import CurveLoop
from anima.primitives.group import Group
from anima.primitives.lines import Segment
from anima.primitives.mesh import Mesh
from tests.test_utils import create_rect_path, create_rect_with_hole_path


def shown(obj) -> bool:
    return not obj.object.hide_render


def make_mesh() -> Mesh:
    mesh = Mesh()
    mesh.set_mesh([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [(0, 1, 2, 3)])
    return mesh


def make_segments(n: int = 3) -> list[Segment]:
    return [Segment((i, 0), (i + 1, 0)) for i in range(n)]


class Recorder(Effect):
    """An effect that records the progress it is given."""

    def __init__(self, target):
        super().__init__(target)
        self.calls: list[float] = []

    def _apply(self, progress: float, elapsed: timedelta | None) -> None:
        self.calls.append(progress)


class TestEffectBase:
    def test_apply_clamps(self):
        reveal = Recorder(Group())
        reveal.apply(-1.0)
        reveal.apply(2.0)
        assert reveal.calls == [0.0, 1.0]
        assert reveal.progress == 1.0

    def test_apply_skips_repeated_progress(self):
        reveal = Recorder(Group())
        assert reveal.progress is None
        reveal.apply(0.5)
        reveal.apply(0.5)
        assert reveal.calls == [0.5]

    def test_invalidate_forces_reapplication(self):
        reveal = Recorder(Group())
        reveal.apply(0.5)
        reveal.invalidate()
        assert reveal.progress is None
        reveal.apply(0.5)
        assert reveal.calls == [0.5, 0.5]

    def test_compositions_preserve_outer_elapsed_time(self):
        observed = []

        def callback(t):
            observed.append(t)

        children = [make_mesh()]
        effects = [
            Together(Group(), [Callback(callback)]),
            Stagger(Group(children), child_effect=lambda child: Callback(callback)),
            Phase(Group(), [(Callback(callback), 0.25, 0.75)]),
        ]
        elapsed = timedelta(seconds=2)

        for effect in effects:
            effect.apply(0.5, elapsed)
            effect.apply(0.5, timedelta(seconds=3))

        assert observed == [elapsed, timedelta(seconds=3)] * 3


class TestDraw:
    def test_draws_along_the_curve(self):
        segment = Segment((0, 0), (4, 0))
        reveal = Draw(segment)
        reveal.apply(0.25)
        assert segment.param_0 == 0.0
        assert segment.param_1 == pytest.approx(0.25)
        reveal.apply(1.0)
        assert segment.param_1 == 1.0
        reveal.apply(0.0)
        assert segment.param_1 == 0.0


class TestScale:
    def test_rejects_non_positive_start_scale(self):
        with pytest.raises(ValueError):
            Scale(make_mesh(), from_scale=0.0)

    def test_scales_without_changing_opacity_or_visibility(self):
        mesh = make_mesh()
        mesh.opacity = 0.8
        reveal = Scale(mesh, from_scale=0.5)
        reveal.apply(0.0)
        assert shown(mesh)
        assert mesh.opacity == pytest.approx(0.8)
        assert tuple(mesh.object.delta_scale) == pytest.approx((0.5, 0.5, 0.5))

        reveal.apply(0.5)
        assert shown(mesh)
        assert mesh.opacity == pytest.approx(0.8)
        assert tuple(mesh.object.delta_scale) == pytest.approx((0.75,) * 3)

        reveal.apply(1.0)
        assert shown(mesh)
        assert mesh.opacity == pytest.approx(0.8)
        assert tuple(mesh.object.delta_scale) == pytest.approx((1.0,) * 3)
        assert tuple(mesh.object.delta_location) == pytest.approx((0.0, 0.0, 0.0))

    def test_does_not_touch_the_objects_own_transform(self):
        mesh = make_mesh()
        mesh.set_location(3, 4, 5)
        Scale(mesh, pivot=(1, 1, 0)).apply(0.3)
        assert tuple(mesh.location) == pytest.approx((3, 4, 5))
        assert tuple(mesh.scale) == pytest.approx((1, 1, 1))

    @pytest.mark.parametrize("scale", [1.0, 2.0])
    @pytest.mark.parametrize("angle", [0.0, 0.7])
    def test_pivot_stays_fixed_as_it_grows(self, scale, angle):
        mesh = make_mesh()
        mesh.set_scale(scale, scale, scale)
        mesh.set_rotation(0, 0, angle)
        pivot = Vector((0.5, 0.5, 0.0))
        reveal = Scale(mesh, from_scale=0.4, pivot=pivot)
        reveal.apply(1.0)
        full = self._placed(mesh, pivot)
        for progress in (0.0, 0.3, 0.8):
            reveal.apply(progress)
            assert self._placed(mesh, pivot) == pytest.approx(full, abs=1e-6)

    @staticmethod
    def _placed(mesh, pivot) -> tuple[float, ...]:
        """Return where the pivot is in the parent's frame (`matrix_basis` includes the delta transforms)."""
        return tuple((mesh.object.matrix_basis @ pivot.to_4d()).to_3d())


class TestFade:
    def test_changes_opacity_without_scaling(self):
        mesh = make_mesh()
        reveal = Fade(mesh)
        reveal.apply(0.0)
        assert not shown(mesh)
        assert mesh.opacity == pytest.approx(0.0)
        assert tuple(mesh.object.delta_scale) == pytest.approx((1.0, 1.0, 1.0))
        reveal.apply(0.4)
        assert shown(mesh)
        assert mesh.opacity == pytest.approx(0.4)
        assert tuple(mesh.object.delta_scale) == pytest.approx((1.0, 1.0, 1.0))


class TestTogether:
    def test_combines_fade_and_scale(self):
        mesh = make_mesh()
        reveal = Together(mesh, [Fade(mesh), Scale(mesh, from_scale=0.5)])

        reveal.apply(0.0)
        assert not shown(mesh)
        assert mesh.opacity == pytest.approx(0.0)
        assert tuple(mesh.object.delta_scale) == pytest.approx((0.5, 0.5, 0.5))

        reveal.apply(0.5)
        assert shown(mesh)
        assert mesh.opacity == pytest.approx(0.5)
        assert tuple(mesh.object.delta_scale) == pytest.approx((0.75, 0.75, 0.75))

    def test_invalidate_reaches_components(self):
        a, b = Recorder(Group()), Recorder(Group())
        reveal = Together(Group(), [a, b])
        reveal.apply(0.5)
        reveal.invalidate()
        assert a.progress is None
        assert b.progress is None


class TestStagger:
    def test_reveals_children_in_turn(self):
        segments = make_segments(3)
        group = Group(segments)
        reveal = Stagger(group, lag_ratio=1.0, child_effect=Draw)
        reveal.apply(0.5)
        assert [s.param_1 for s in segments] == pytest.approx([1.0, 0.5 * 3 - 1, 0.0])
        reveal.apply(1.0)
        assert [s.param_1 for s in segments] == [1.0, 1.0, 1.0]
        reveal.apply(0.0)
        assert [s.param_1 for s in segments] == [0.0, 0.0, 0.0]

    def test_no_lag_reveals_children_together(self):
        segments = make_segments(3)
        reveal = Stagger(Group(segments), lag_ratio=0.0, child_effect=Draw)
        reveal.apply(0.4)
        assert [s.param_1 for s in segments] == pytest.approx([0.4] * 3)

    def test_order_decides_who_goes_first(self):
        segments = make_segments(3)
        reveal = Stagger(Group(segments), lag_ratio=1.0, order=reversed_order, child_effect=Draw)
        reveal.apply(1 / 3)
        assert [s.param_1 for s in segments] == pytest.approx([0.0, 0.0, 1.0])

    def test_rejects_an_order_that_is_not_a_permutation(self):
        with pytest.raises(ValueError):
            Stagger(Group(make_segments(3)), order=lambda items: [0, 0, 1], child_effect=Draw)

    def test_custom_child_effect(self):
        children = [make_mesh(), make_mesh()]
        made: list[Recorder] = []

        def make(child):
            made.append(Recorder(child))
            return made[-1]

        reveal = Stagger(Group(children), lag_ratio=1.0, child_effect=make)
        reveal.apply(0.5)
        assert [r.calls for r in made] == [[1.0], [0.0]]

    def test_explicit_children(self):
        segments = make_segments(3)
        group = Group(segments)
        reveal = Stagger(group, children=segments[:2], lag_ratio=1.0, child_effect=Draw)
        reveal.apply(0.0)
        assert [s.param_1 for s in segments] == [0.0, 0.0, 1.0]  # The third is not revealed, so it is untouched.

    def test_invalidate_reaches_children(self):
        group = Group(make_segments(2))
        reveal = Stagger(group, child_effect=Draw)
        reveal.apply(1.0)
        reveal.invalidate()
        assert all(child.progress is None for child in reveal.effects)


class TestPhase:
    def test_runs_phases_in_their_windows(self):
        a, b = Recorder(Group()), Recorder(Group())
        reveal = Phase(Group(), [(a, 0.0, 0.5), (b, 0.5, 1.0)])
        reveal.apply(0.25)
        assert (a.calls, b.calls) == ([0.5], [0.0])
        reveal.apply(0.75)
        assert (a.calls, b.calls) == ([0.5, 1.0], [0.0, 0.5])

    def test_windows_can_overlap(self):
        a, b = Recorder(Group()), Recorder(Group())
        reveal = Phase(Group(), [(a, 0.0, 0.8), (b, 0.4, 1.0)])
        reveal.apply(0.6)
        assert a.calls == [pytest.approx(0.75)]
        assert b.calls == [pytest.approx(1 / 3)]

    @pytest.mark.parametrize("window", [(-0.1, 0.5), (0.2, 1.1), (0.6, 0.4)])
    def test_rejects_bad_windows(self, window):
        with pytest.raises(ValueError):
            Phase(Group(), [(Recorder(Group()), *window)])

    def test_invalidate_reaches_phases(self):
        a = Recorder(Group())
        reveal = Phase(Group(), [(a, 0.0, 1.0)])
        reveal.apply(1.0)
        reveal.invalidate()
        assert a.progress is None


class TestGlyphWriteOn:
    def test_outline_is_drawn_before_the_fill_fades_in(self):
        glyph = Glyph(create_rect_path(), name="G")
        effect = glyph_write_on(glyph)
        loops = list(glyph.border.children)
        assert all(isinstance(loop, CurveLoop) for loop in loops)

        effect.apply(0.0)
        assert not shown(glyph.body)
        assert loops[0].param_1 == 0.0

        effect.apply(Glyph.BORDER_REVEAL_WINDOW[1])
        assert loops[0].param_1 == pytest.approx(1.0)
        assert glyph.body.opacity < 1.0

        effect.apply(0.75)
        assert glyph.body.opacity == pytest.approx(0.5)
        assert tuple(glyph.body.object.delta_scale) == pytest.approx((1.0, 1.0, 1.0))

        effect.apply(1.0)
        assert glyph.body.opacity == pytest.approx(1.0)
        assert shown(glyph.body)

    def test_loops_of_a_glyph_with_a_hole_are_drawn_together(self):
        glyph = Glyph(create_rect_with_hole_path(), name="H")
        loops = list(glyph.border.children)
        assert len(loops) == 2
        glyph_write_on(glyph).apply(0.35)
        assert loops[0].param_1 == pytest.approx(loops[1].param_1)
        assert 0.0 < loops[0].param_1 < 1.0

    def test_glyph_group_staggers_its_glyphs(self):
        glyphs = [Glyph(create_rect_path(), name=f"G{i}") for i in range(3)]
        reveal = Stagger(GlyphGroup(glyphs), child_effect=glyph_write_on)
        assert isinstance(reveal, Stagger)
        reveal.apply(0.0)
        assert all(not shown(g.body) for g in glyphs)
        reveal.apply(1.0)
        assert all(shown(g.body) and g.body.opacity == pytest.approx(1.0) for g in glyphs)
