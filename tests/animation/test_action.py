"""Tests for F-curve progress tracks, appearance actions and the scheduler."""

import bpy
import pytest

import anima.animation.updater as updater_module
from anima.animation.action import (
    Appearance,
    Enter,
    Exit,
    FCurvePreset,
    KeyframedProperty,
)
from anima.animation.reveal import Fade, Reveal, Scale, Stagger, Together
from anima.animation.scheduler import Scheduler, play
from anima.animation.updater import Updater
from anima.primitives.group import Group
from anima.primitives.lines import Segment
from anima.primitives.mesh import Mesh


@pytest.fixture(autouse=True)
def clean_scheduler():
    Scheduler.reset()
    scene = bpy.context.scene
    old_frame = scene.frame_current
    yield
    Scheduler.reset()
    scene.frame_set(old_frame)


def at(frame: int) -> None:
    bpy.context.scene.frame_set(frame)


def make_segment() -> Segment:
    return Segment((0, 0), (1, 0))


def make_mesh() -> Mesh:
    mesh = Mesh()
    mesh.set_mesh([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [(0, 1, 2, 3)])
    return mesh


class TestKeyframedProperty:
    def test_creates_a_keyframed_custom_property(self):
        track = KeyframedProperty((10, 30), (0.2, 0.8), preset=FCurvePreset.LINEAR)
        assert track.driver[track.PROPERTY_NAME] == pytest.approx(0.2)
        assert track.fcurve.data_path == '["progress"]'
        assert [value for point in track.fcurve.keyframe_points for value in point.co] == pytest.approx(
            [10.0, 0.2, 30.0, 0.8]
        )
        assert all(point.interpolation == "LINEAR" for point in track.fcurve.keyframe_points)

    def test_blender_evaluates_the_fcurve_value(self):
        track = KeyframedProperty((10, 30), (0.0, 1.0), preset=FCurvePreset.LINEAR)
        at(10)
        assert track.value == 0.0
        at(20)
        assert track.value == pytest.approx(0.5)
        at(30)
        assert track.value == 1.0

    def test_interpolation_and_easing_presets_are_applied(self):
        track = KeyframedProperty(
            (10, 30),
            preset=FCurvePreset.QUAD_IN_OUT,
        )
        assert all(point.interpolation == "QUAD" for point in track.fcurve.keyframe_points)
        assert all(point.easing == "EASE_IN_OUT" for point in track.fcurve.keyframe_points)
        assert track.fcurve.evaluate(15) < 0.25
        assert track.fcurve.evaluate(25) > 0.75

    def test_fcurve_can_be_edited_directly(self):
        track = KeyframedProperty((10, 30), preset=FCurvePreset.LINEAR)
        track.fcurve.keyframe_points[1].co.y = 0.6
        track.fcurve.update()
        at(30)
        assert track.value == pytest.approx(0.6)

    def test_add_keyframe(self):
        track = KeyframedProperty((10, 30), preset=FCurvePreset.LINEAR)
        track.add_keyframe(20, 0.25)
        assert [value for point in track.fcurve.keyframe_points for value in point.co] == pytest.approx(
            [10.0, 0.0, 20.0, 0.25, 30.0, 1.0]
        )

    @pytest.mark.parametrize("frame_range", [(1, 1), (2, 1), (1.5, 3), (True, 4)])
    def test_rejects_invalid_frame_ranges(self, frame_range):
        with pytest.raises((TypeError, ValueError)):
            KeyframedProperty(frame_range)

    def test_rejects_invalid_preset(self):
        with pytest.raises(TypeError):
            KeyframedProperty((1, 2), preset="LINEAR")


class TestAppearanceActions:
    def test_enter_and_exit_default_ranges(self):
        segment = make_segment()
        enter = Enter(segment, (10, 30), preset=FCurvePreset.LINEAR)
        exit_action = Exit(segment, (40, 60), preset=FCurvePreset.LINEAR)
        at(10)
        enter.apply()
        assert segment.param_1 == 0.0
        at(20)
        enter.apply()
        assert segment.param_1 == pytest.approx(0.5)
        at(40)
        exit_action.apply()
        assert segment.param_1 == 1.0
        at(60)
        exit_action.apply()
        assert segment.param_1 == 0.0

    def test_defaults_to_the_targets_reveal_strategy(self):
        mesh_reveal = Enter(make_mesh(), (1, 20)).reveal
        assert isinstance(mesh_reveal, Together)
        assert [type(component) for component in mesh_reveal.reveals] == [Fade, Scale]
        assert isinstance(Enter(Group([make_segment()]), (1, 20)).reveal, Stagger)
        assert isinstance(Enter(make_segment(), (1, 20)).reveal, Reveal)

    def test_accepts_a_selected_reveal(self):
        mesh = make_mesh()
        reveal = Fade(mesh)
        assert Enter(mesh, (1, 20), reveal=reveal).reveal is reveal

    def test_rejects_a_reveal_of_another_object(self):
        with pytest.raises(ValueError):
            Enter(make_mesh(), (1, 20), reveal=Fade(make_mesh()))

    def test_can_bind_a_shared_track(self):
        segment = make_segment()
        track = KeyframedProperty((10, 30), preset=FCurvePreset.LINEAR)
        action = Appearance(segment, track)
        assert action.track is track


class TestScheduler:
    def test_adding_applies_the_current_frame(self):
        segment = make_segment()
        play(Enter(segment, (1, 20), preset=FCurvePreset.LINEAR))
        assert segment.param_1 == 0.0

    def test_scrubbing_is_consistent(self):
        segment = make_segment()
        play(Enter(segment, (10, 30), preset=FCurvePreset.LINEAR))
        for frame, expected in ((10, 0.0), (20, 0.5), (30, 1.0), (15, 0.25), (25, 0.75), (20, 0.5)):
            at(frame)
            assert segment.param_1 == pytest.approx(expected)

    def test_enter_then_exit(self):
        mesh = make_mesh()
        play(
            Enter(mesh, (10, 20), preset=FCurvePreset.LINEAR),
            Exit(mesh, (30, 40), preset=FCurvePreset.LINEAR),
        )
        for frame, opacity in ((10, 0.0), (15, 0.5), (25, 1.0), (35, 0.5), (45, 0.0), (15, 0.5)):
            at(frame)
            assert mesh.opacity == pytest.approx(opacity), frame

    def test_switching_actions_invalidates_cached_reveal_state(self):
        mesh = make_mesh()
        play(
            Enter(mesh, (10, 20), preset=FCurvePreset.LINEAR),
            Exit(mesh, (30, 40), preset=FCurvePreset.LINEAR),
        )
        at(20)
        at(40)
        assert mesh.object.hide_render
        at(20)
        assert not mesh.object.hide_render
        assert mesh.opacity == pytest.approx(1.0)

    def test_targets_are_independent(self):
        a, b = make_segment(), make_segment()
        play(
            Enter(a, (10, 20), preset=FCurvePreset.LINEAR),
            Enter(b, (20, 30), preset=FCurvePreset.LINEAR),
        )
        at(20)
        assert (a.param_1, b.param_1) == (1.0, 0.0)
        at(25)
        assert (a.param_1, b.param_1) == pytest.approx((1.0, 0.5))

    def test_actions_lists_everything(self):
        a, b = Enter(make_segment(), (1, 10)), Enter(make_segment(), (10, 20))
        play(a, b)
        assert set(Scheduler.instance().actions) == {a, b}

    def test_current_frame_includes_subframe(self):
        scene = bpy.context.scene
        scene.frame_set(25, subframe=0.5)
        assert Scheduler.current_frame() == pytest.approx(25.5)


class TestHandlers:
    def test_frame_changes_drive_actions(self):
        segment = make_segment()
        play(Enter(segment, (10, 30), preset=FCurvePreset.LINEAR))
        at(20)
        assert segment.param_1 == pytest.approx(0.5)
        at(30)
        assert segment.param_1 == pytest.approx(1.0)
        at(15)
        assert segment.param_1 == pytest.approx(0.25)

    def test_refresh_samples_the_fcurve_even_without_a_handler_event(self):
        segment = make_segment()
        play(Enter(segment, (10, 30), preset=FCurvePreset.LINEAR))
        at(20)
        assert segment.param_1 == pytest.approx(0.5)
        bpy.context.scene.frame_current = 30
        Scheduler.instance().refresh()
        assert segment.param_1 == pytest.approx(1.0)
        at(30)
        assert segment.param_1 == 1.0

    def test_reset_stops_the_handler(self):
        segment = make_segment()
        play(Enter(segment, (10, 30), preset=FCurvePreset.LINEAR))
        Scheduler.reset()
        at(30)
        assert segment.param_1 == 0.0

    def test_reset_forgets_actions(self):
        play(Enter(make_segment(), (1, 10)))
        Scheduler.reset()
        assert Scheduler.instance().actions == []


def test_updater_instance_is_a_singleton():
    assert Updater.instance() is Updater.instance() is Updater()


def test_updater_dispatches_multiple_callbacks():
    calls = []
    updater = Updater.instance()

    def callback():
        calls.append(bpy.context.scene.frame_current)

    updater.add_callback(callback)
    try:
        at(2)
        assert calls == [2]
    finally:
        updater.remove_callback(callback)
    assert updater_module._dispatch_frame_change in bpy.app.handlers.frame_change_pre
