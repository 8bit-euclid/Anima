"""Tests for F-curve progress tracks, actions and the scheduler."""

from datetime import timedelta

import bpy
import pytest

import anima.animation.scheduler as scheduler_module
from anima.animation.action import (
    Action,
    Enter,
    Exit,
    FCurvePreset,
    KeyframedProperty,
)
from anima.animation.effects import Callback, Draw, Effect, Fade, Scale, Stagger, Together
from anima.animation.scheduler import Scheduler
from anima.animation.timeline import frame_rate, from_frame
from anima.primitives.group import Group
from anima.primitives.lines import Segment
from anima.primitives.mesh import Mesh


@pytest.fixture(autouse=True)
def clean_scheduler():
    Scheduler().reset()
    scene = bpy.context.scene
    old_frame = scene.frame_current
    yield
    Scheduler().reset()
    scene.frame_set(old_frame)


def at(frame: int) -> None:
    bpy.context.scene.frame_set(frame)


def frames(count: int) -> timedelta:
    """Return the duration of a number of frames."""
    return timedelta(seconds=count / frame_rate())


def wait_until(frame: int) -> None:
    """Advance the scheduler's cursor to a frame."""
    Scheduler().wait(from_frame(frame) - Scheduler().end_time)


def make_segment() -> Segment:
    return Segment((0, 0), (1, 0))


def enter_draw(target, duration, **kwargs) -> Enter:
    """Create an enter action that explicitly draws a curve."""
    return Enter(Draw(target), duration, **kwargs)


def exit_draw(target, duration, **kwargs) -> Exit:
    """Create an exit action that explicitly draws a curve."""
    return Exit(Draw(target), duration, **kwargs)


def enter_fade(target, duration, **kwargs) -> Enter:
    """Create an enter action that explicitly fades an object."""
    return Enter(Fade(target), duration, **kwargs)


def exit_fade(target, duration, **kwargs) -> Exit:
    """Create an exit action that explicitly fades an object."""
    return Exit(Fade(target), duration, **kwargs)


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


class TestEffectActions:
    def test_enter_and_exit_default_ranges(self):
        segment = make_segment()
        enter = enter_draw(segment, frames(20), preset=FCurvePreset.LINEAR)
        exit_action = exit_draw(segment, frames(20), preset=FCurvePreset.LINEAR)
        enter.place(from_frame(10))
        exit_action.place(from_frame(40))
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

    def test_action_requires_an_explicit_effect(self):
        mesh = make_mesh()
        effect = Together(mesh, [Fade(mesh), Scale(mesh)])
        action = Enter(effect, frames(19))
        assert action.effect is effect
        assert action.target is mesh

    def test_rejects_non_effects(self):
        with pytest.raises(TypeError):
            Action(frames(10), make_mesh())

    @pytest.mark.parametrize("duration", [timedelta(0), timedelta(seconds=-1)])
    def test_rejects_nonpositive_durations(self, duration):
        with pytest.raises(ValueError):
            enter_draw(make_segment(), duration)

    def test_has_no_timing_until_placed(self):
        action = enter_draw(make_segment(), frames(10))
        assert not action.placed
        with pytest.raises(RuntimeError):
            _ = action.start_frame
        with pytest.raises(RuntimeError):
            _ = action.start_time

    def test_can_only_be_placed_once(self):
        action = enter_draw(make_segment(), frames(10))
        action.place(timedelta(0))
        with pytest.raises(RuntimeError):
            action.place(timedelta(seconds=5))
        with pytest.raises(RuntimeError):
            Scheduler().add_action(action)


class TestScheduler:
    def test_adding_applies_the_current_frame(self):
        segment = make_segment()
        Scheduler().add_action(enter_draw(segment, frames(19), preset=FCurvePreset.LINEAR))
        assert segment.param_1 == 0.0

    def test_actions_run_sequentially_from_the_cursor(self):
        scheduler = Scheduler()
        first = enter_draw(make_segment(), frames(20))
        second = enter_draw(make_segment(), frames(10))
        scheduler.add_action(first)
        scheduler.wait(frames(5))
        scheduler.add_action(second)
        assert (first.start_frame, first.stop_frame) == (1, 21)
        assert (second.start_frame, second.stop_frame) == (26, 36)
        assert scheduler.end_time == frames(35)

    def test_actions_added_together_run_in_parallel(self):
        scheduler = Scheduler()
        short, long = enter_draw(make_segment(), frames(10)), enter_draw(make_segment(), frames(30))
        scheduler.add_actions(short, long)
        assert short.start_frame == long.start_frame == 1
        assert scheduler.end_time == frames(30)

    def test_with_previous_starts_together_and_the_cursor_follows_the_latest_end(self):
        scheduler = Scheduler()
        a, b, after = (
            enter_draw(make_segment(), frames(20)),
            enter_draw(make_segment(), frames(30)),
            enter_draw(make_segment(), frames(5)),
        )
        scheduler.add_action(a)
        scheduler.add_action(b, with_previous=True)
        assert a.start_frame == b.start_frame == 1
        assert scheduler.end_time == frames(30)
        scheduler.add_action(after)
        assert after.start_frame == 31

    def test_shorter_with_previous_action_does_not_shrink_the_cursor(self):
        scheduler = Scheduler()
        scheduler.add_action(enter_draw(make_segment(), frames(30)))
        scheduler.add_action(enter_draw(make_segment(), frames(10)), with_previous=True)
        assert scheduler.end_time == frames(30)

    def test_with_previous_ignores_waits_and_groups_follow_the_previous_start(self):
        scheduler = Scheduler()
        scheduler.add_action(enter_draw(make_segment(), frames(10)))
        scheduler.wait(frames(40))
        group_member = enter_draw(make_segment(), frames(10))
        scheduler.add_actions(group_member, with_previous=True)
        assert group_member.start_frame == 1

    def test_with_previous_without_history_starts_at_zero(self):
        action = enter_draw(make_segment(), frames(10))
        Scheduler().add_action(action, with_previous=True)
        assert action.start_frame == 1

    def test_reset_forgets_the_previous_start(self):
        scheduler = Scheduler()
        scheduler.wait(frames(40))
        scheduler.add_action(enter_draw(make_segment(), frames(10)))
        scheduler.reset()
        action = enter_draw(make_segment(), frames(10))
        scheduler.add_action(action, with_previous=True)
        assert action.start_frame == 1

    def test_callbacks_accept_with_previous(self):
        scheduler = Scheduler()
        first = enter_draw(make_segment(), frames(20))
        scheduler.add_action(first)
        scheduler.add_callback(lambda u: None, duration=frames(10), with_previous=True)
        assert [a.start_frame for a in scheduler.actions] == [1, 1]

    def test_cursor_accumulates_without_rounding_drift(self):
        scheduler = Scheduler()
        for _ in range(3):
            scheduler.add_action(enter_draw(make_segment(), timedelta(seconds=1.3)))
        assert scheduler.end_time == timedelta(seconds=3.9)

    def test_reset_returns_the_cursor_to_zero(self):
        scheduler = Scheduler()
        scheduler.wait("00:02")
        scheduler.reset()
        assert scheduler.end_time == timedelta(0)

    def test_scrubbing_is_consistent(self):
        segment = make_segment()
        wait_until(10)
        Scheduler().add_action(enter_draw(segment, frames(20), preset=FCurvePreset.LINEAR))
        for frame, expected in ((10, 0.0), (20, 0.5), (30, 1.0), (15, 0.25), (25, 0.75), (20, 0.5)):
            at(frame)
            assert segment.param_1 == pytest.approx(expected)

    def test_enter_then_exit(self):
        mesh = make_mesh()
        scheduler = Scheduler()
        wait_until(10)
        scheduler.add_action(enter_fade(mesh, frames(10), preset=FCurvePreset.LINEAR))
        wait_until(30)
        scheduler.add_action(exit_fade(mesh, frames(10), preset=FCurvePreset.LINEAR))
        for frame, opacity in ((10, 0.0), (15, 0.5), (25, 1.0), (35, 0.5), (45, 0.0), (15, 0.5)):
            at(frame)
            assert mesh.opacity == pytest.approx(opacity), frame

    def test_switching_actions_invalidates_cached_reveal_state(self):
        mesh = make_mesh()
        scheduler = Scheduler()
        wait_until(10)
        scheduler.add_action(enter_fade(mesh, frames(10), preset=FCurvePreset.LINEAR))
        wait_until(30)
        scheduler.add_action(exit_fade(mesh, frames(10), preset=FCurvePreset.LINEAR))
        at(20)
        at(40)
        assert mesh.object.hide_render
        at(20)
        assert not mesh.object.hide_render
        assert mesh.opacity == pytest.approx(1.0)

    def test_targets_are_independent(self):
        a, b = make_segment(), make_segment()
        scheduler = Scheduler()
        wait_until(10)
        scheduler.add_action(enter_draw(a, frames(10), preset=FCurvePreset.LINEAR))
        scheduler.add_action(enter_draw(b, frames(10), preset=FCurvePreset.LINEAR))
        at(20)
        assert (a.param_1, b.param_1) == (1.0, 0.0)
        at(25)
        assert (a.param_1, b.param_1) == pytest.approx((1.0, 0.5))

    def test_actions_lists_everything(self):
        a, b = enter_draw(make_segment(), frames(9)), enter_draw(make_segment(), frames(10))
        Scheduler().add_actions(a, b)
        assert set(Scheduler().actions) == {a, b}

    def test_evaluate_uses_elapsed_time(self):
        segment = make_segment()
        scheduler = Scheduler()
        scheduler.add_action(enter_draw(segment, timedelta(seconds=1), preset=FCurvePreset.LINEAR))
        scheduler.evaluate(timedelta(seconds=0.5))
        assert segment.param_1 == pytest.approx(0.5)

    def test_wait_rejects_negative_durations(self):
        with pytest.raises(ValueError):
            Scheduler().wait(timedelta(seconds=-1))


class TestHandlers:
    def test_frame_changes_drive_actions(self):
        segment = make_segment()
        wait_until(10)
        Scheduler().add_action(enter_draw(segment, frames(20), preset=FCurvePreset.LINEAR))
        at(20)
        assert segment.param_1 == pytest.approx(0.5)
        at(30)
        assert segment.param_1 == pytest.approx(1.0)
        at(15)
        assert segment.param_1 == pytest.approx(0.25)

    def test_refresh_samples_the_fcurve_even_without_a_handler_event(self):
        segment = make_segment()
        wait_until(10)
        Scheduler().add_action(enter_draw(segment, frames(20), preset=FCurvePreset.LINEAR))
        at(20)
        assert segment.param_1 == pytest.approx(0.5)
        bpy.context.scene.frame_current = 30
        Scheduler().refresh()
        assert segment.param_1 == pytest.approx(1.0)
        at(30)
        assert segment.param_1 == 1.0

    def test_reset_stops_the_handler(self):
        segment = make_segment()
        wait_until(10)
        Scheduler().add_action(enter_draw(segment, frames(20), preset=FCurvePreset.LINEAR))
        Scheduler().reset()
        at(30)
        assert segment.param_1 == 0.0

    def test_reset_forgets_actions(self):
        Scheduler().add_action(enter_draw(make_segment(), frames(9)))
        Scheduler().reset()
        assert Scheduler().actions == []


def test_scheduler_is_a_singleton_that_dispatches_frame_changes():
    assert Scheduler() is Scheduler()
    assert scheduler_module._dispatch_frame_change in bpy.app.handlers.frame_change_pre


class TestCallbacks:
    def test_receives_progress_and_elapsed_time(self):
        observed = []
        scheduler = Scheduler()
        scheduler.add_callback(
            lambda u, t: observed.append((u, t)), duration=timedelta(seconds=1), preset=FCurvePreset.LINEAR
        )
        observed.clear()
        at(13)
        u, t = observed[-1]
        assert u == pytest.approx(0.5)
        assert t.total_seconds() == pytest.approx(0.5)

    def test_parameters_are_matched_by_name(self):
        seen = {}
        scheduler = Scheduler()
        scheduler.add_callback(lambda t: seen.setdefault("t", t), duration=frames(10))
        scheduler.add_callback(lambda u: seen.setdefault("u", u), duration=frames(10))
        assert set(seen) == {"t", "u"}

    @pytest.mark.parametrize("function", [lambda: None, lambda x: None, lambda u, x: None, lambda *args: None])
    def test_rejects_other_signatures(self, function):
        with pytest.raises(TypeError):
            Callback(function)

    def test_decorator_form_registers_and_returns_the_function(self):
        calls = []

        @Scheduler().add_callback(duration=frames(10))
        def draw(u):
            calls.append(u)

        assert callable(draw)
        assert calls == [0.0]
        assert len(Scheduler().actions) == 1

    def test_runs_inside_the_window_and_settles_on_both_sides(self):
        calls = []
        scheduler = Scheduler()
        wait_until(10)
        scheduler.add_callback(lambda u: calls.append(u), duration=frames(10), preset=FCurvePreset.LINEAR)
        at(1)
        assert calls[-1] == 0.0
        calls.clear()
        at(5)
        at(8)
        assert calls == []
        at(15)
        assert calls == [pytest.approx(0.5)]
        at(40)
        assert calls[-1] == 1.0
        calls.clear()
        at(50)
        assert calls == []
        at(2)
        assert calls == [0.0]

    def test_jumping_past_the_window_draws_the_final_state(self):
        calls = []
        wait_until(10)
        Scheduler().add_callback(lambda u: calls.append(u), duration=frames(10))
        calls.clear()
        at(100)
        assert calls == [1.0]

    def test_elapsed_time_is_clamped_to_the_window(self):
        calls = []
        wait_until(10)
        Scheduler().add_callback(lambda t: calls.append(t), duration=frames(10))
        at(100)
        assert calls[-1] == frames(10)
        at(1)
        assert calls[-1] == timedelta(0)

    def test_callbacks_follow_the_cursor(self):
        scheduler = Scheduler()
        scheduler.add_callback(lambda u: None, duration=frames(10))
        second = Action(frames(10), Callback(lambda u: None))
        scheduler.add_action(second)
        assert second.start_frame == 11

    def test_refresh_calls_the_function_again(self):
        calls = []
        Scheduler().add_callback(lambda u: calls.append(u), duration=frames(10))
        calls.clear()
        Scheduler().refresh()
        assert calls == [0.0]
