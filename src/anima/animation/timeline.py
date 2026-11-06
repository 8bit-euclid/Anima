"""Parsing and conversion of elapsed animation time to and from Blender frames.

This module owns the frame-rate calculation and the convention that zero elapsed time is frame 1.
"""

from __future__ import annotations

from datetime import timedelta
from math import isfinite
from typing import TypeAlias

import bpy

TimeInput: TypeAlias = timedelta | str

ORIGIN_FRAME = 1


def parse_time(time_str: str) -> timedelta:
    """Parse a time string of the form mm:ss or mm:ss:mmm.

    Args:
        time_str: The time string to convert, for example "01:30" or "00:02:500".

    Returns:
        The corresponding duration.

    Raises:
        AssertionError: If the time string is not in an accepted format.
    """
    units = time_str.split(":")
    assert len(units) in [2, 3], "Accepted time formats are mm:ss and mm:ss:mmm"
    assert len(units[0]) == 2
    assert len(units[1]) == 2

    delta = timedelta(minutes=int(units[0]), seconds=int(units[1]))
    if len(units) == 3:
        assert len(units[2]) == 3
        delta += timedelta(milliseconds=int(units[2]))
    return delta


def frame_rate(scene: bpy.types.Scene | None = None) -> float:
    """Return a scene's effective frame rate in frames per second.

    This is the only place that combines Blender's `fps` and `fps_base`.

    Args:
        scene: Scene supplying the frame rate. Defaults to the active scene.

    Returns:
        The frame rate, `fps / fps_base`.

    Raises:
        ValueError: If the frame rate is not positive and finite.
    """
    render = (scene or bpy.context.scene).render
    fps = render.fps / render.fps_base
    if not isfinite(fps) or fps <= 0:
        raise ValueError(f"Scene frame rate must be positive and finite, got {fps}.")
    return fps


def as_timedelta(value: TimeInput) -> timedelta:
    """Convert a supported time value to a duration.

    Args:
        value: A `timedelta` or a time string accepted by `parse_time`.

    Returns:
        The parsed duration.

    Raises:
        TypeError: If `value` is not a supported time representation.
        ValueError: If the time is negative.
    """
    if isinstance(value, str):
        value = parse_time(value)
    if not isinstance(value, timedelta):
        raise TypeError(f"Expected timedelta or time string, got {type(value).__name__}.")
    if value.total_seconds() < 0:
        raise ValueError("Animation time cannot be negative.")
    return value


def to_frame(value: TimeInput, *, scene: bpy.types.Scene | None = None) -> int:
    """Convert elapsed time from frame 1 to the nearest Blender frame.

    Args:
        value: Elapsed time from the animation origin (frame 1).
        scene: Scene supplying the frame rate. Defaults to the active scene.

    Returns:
        The nearest Blender frame, with zero elapsed time mapping to frame 1.

    Raises:
        ValueError: If the scene has an invalid frame rate.
    """
    elapsed = as_timedelta(value).total_seconds()
    return round(elapsed * frame_rate(scene)) + ORIGIN_FRAME


def from_frame(frame: float, *, scene: bpy.types.Scene | None = None) -> timedelta:
    """Convert a Blender frame position to elapsed time from frame 1.

    Args:
        frame: Blender frame position, including an optional fractional subframe.
        scene: Scene supplying the frame rate. Defaults to the active scene.

    Returns:
        Elapsed time as a `timedelta`.

    Raises:
        ValueError: If the scene has an invalid frame rate.
    """
    return timedelta(seconds=(frame - ORIGIN_FRAME) / frame_rate(scene))


def range_to_frames(
    start_time: TimeInput, duration: TimeInput, *, scene: bpy.types.Scene | None = None
) -> tuple[int, int]:
    """Convert an elapsed start time and duration to integer Blender keyframe positions.

    Args:
        start_time: Elapsed time from frame 1.
        duration: Positive length of the animation.
        scene: Scene supplying the frame rate. Defaults to the active scene.

    Returns:
        The inclusive start and end frames, rounded independently to the nearest frame.

    Raises:
        ValueError: If the duration is not positive or rounding produces an invalid frame range.
    """
    start = as_timedelta(start_time)
    length = as_timedelta(duration)
    if length <= timedelta(0):
        raise ValueError("Animation duration must be positive.")
    start_frame = to_frame(start, scene=scene)
    end_frame = to_frame(start + length, scene=scene)
    if end_frame <= start_frame:
        raise ValueError("Animation duration is shorter than the scene's frame resolution.")
    return start_frame, end_frame
