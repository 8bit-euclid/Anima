"""Tests for converting elapsed animation times to Blender frames."""

from datetime import timedelta

import bpy
import pytest

from anima.animation.timeline import as_timedelta, frame_rate, from_frame, parse_time, range_to_frames, to_frame


def test_time_strings_and_timedeltas_are_supported():
    assert as_timedelta("00:01") == timedelta(seconds=1)
    assert as_timedelta("00:01:250") == timedelta(seconds=1, milliseconds=250)
    assert as_timedelta(timedelta(seconds=2)) == timedelta(seconds=2)
    assert as_timedelta(1) == timedelta(seconds=1)
    assert as_timedelta(1.25) == timedelta(seconds=1, milliseconds=250)


def test_elapsed_time_uses_frame_one_as_the_origin():
    scene = bpy.context.scene
    assert to_frame(timedelta(0), scene=scene) == 1
    assert to_frame(timedelta(seconds=1), scene=scene) == round(frame_rate(scene)) + 1
    assert to_frame(1) == round(frame_rate(scene)) + 1
    assert to_frame(1.25) == round(1.25 * frame_rate(scene)) + 1
    assert from_frame(to_frame("00:01"), scene=scene) == timedelta(seconds=1)


def test_parse_time_formats():
    assert parse_time("01:30") == timedelta(minutes=1, seconds=30)
    assert parse_time("00:02:500") == timedelta(seconds=2, milliseconds=500)
    with pytest.raises(AssertionError):
        parse_time("1:30")


def test_frame_conversions_use_the_effective_frame_rate():
    render = bpy.context.scene.render
    fps, fps_base = render.fps, render.fps_base
    try:
        render.fps = 30
        render.fps_base = 1.001
        assert frame_rate() == pytest.approx(30 / 1.001)
        assert to_frame(timedelta(seconds=1)) == round(30 / 1.001) + 1
    finally:
        render.fps = fps
        render.fps_base = fps_base


def test_ranges_convert_start_and_duration():
    scene = bpy.context.scene
    fps = frame_rate(scene)
    start = timedelta(seconds=2 / fps)
    duration = timedelta(seconds=5 / fps)
    assert range_to_frames(start, duration, scene=scene) == (3, 8)


@pytest.mark.parametrize("duration", [timedelta(0), timedelta(microseconds=1), timedelta(seconds=-1)])
def test_ranges_reject_nonpositive_or_negative_durations(duration):
    with pytest.raises(ValueError):
        range_to_frames(timedelta(0), duration)


def test_time_conversion_rejects_unsupported_types():
    with pytest.raises(TypeError):
        to_frame(object())
    with pytest.raises(TypeError):
        to_frame(True)


@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan")])
def test_time_conversion_rejects_nonfinite_seconds(value):
    with pytest.raises(ValueError, match="finite"):
        to_frame(value)
