"""Actions that bind keyframed progress tracks to reveal strategies."""

from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import timedelta
from enum import Enum
from typing import TYPE_CHECKING

import bpy

from anima.animation.timeline import TimeInput, as_timedelta, from_frame, range_to_frames
from anima.primitives.points import Empty

if TYPE_CHECKING:
    from anima.animation.reveal import Reveal
    from anima.primitives.object import Object

__all__ = ["Action", "Appearance", "Callback", "Enter", "Exit", "FCurvePreset", "KeyframedProperty"]


class FCurvePreset(Enum):
    """Named combinations of Blender F-curve interpolation and easing.

    Blender applies interpolation per keyframe to the segment that follows it. The preset therefore configures all
    current keyframes on a `KeyframedProperty`, and newly added keys receive the same setting.

    Attributes:
        CONSTANT: Hold each value until the next keyframe.
        LINEAR: Interpolate linearly between keyed values.
        BEZIER: Use Blender's automatically handled Bézier interpolation.
        EASE_IN: Quadratic ease-in.
        EASE_OUT: Quadratic ease-out.
        EASE_IN_OUT: Quadratic ease-in and ease-out.
        SINE_IN: Sine ease-in.
        SINE_OUT: Sine ease-out.
        SINE_IN_OUT: Sine ease-in and ease-out.
        QUAD_IN: Quadratic ease-in.
        QUAD_OUT: Quadratic ease-out.
        QUAD_IN_OUT: Quadratic ease-in and ease-out.
        CUBIC_IN: Cubic ease-in.
        CUBIC_OUT: Cubic ease-out.
        CUBIC_IN_OUT: Cubic ease-in and ease-out.
    """

    CONSTANT = ("CONSTANT", "AUTO")
    LINEAR = ("LINEAR", "AUTO")
    BEZIER = ("BEZIER", "AUTO")
    EASE_IN = ("QUAD", "EASE_IN")
    EASE_OUT = ("QUAD", "EASE_OUT")
    EASE_IN_OUT = ("QUAD", "EASE_IN_OUT")
    SINE_IN = ("SINE", "EASE_IN")
    SINE_OUT = ("SINE", "EASE_OUT")
    SINE_IN_OUT = ("SINE", "EASE_IN_OUT")
    QUAD_IN = ("QUAD", "EASE_IN")
    QUAD_OUT = ("QUAD", "EASE_OUT")
    QUAD_IN_OUT = ("QUAD", "EASE_IN_OUT")
    CUBIC_IN = ("CUBIC", "EASE_IN")
    CUBIC_OUT = ("CUBIC", "EASE_OUT")
    CUBIC_IN_OUT = ("CUBIC", "EASE_IN_OUT")


class KeyframedProperty:
    """A custom property animated by a Blender F-curve.

    The driver is a separate Empty, not the object whose reveal it controls. The F-curve is exposed so it can be
    further edited using Blender's animation tools or API.

    Values are not restricted to [0, 1]; a reveal strategy clamps them when applied. The Empty's custom property
    reflects Blender's evaluated value after a frame change. Use `value_at` to sample the F-curve during a pre-frame
    callback.

    Attributes:
        driver: The Empty that owns the animated custom property.
        fcurve: The Blender F-curve driving the property.
        preset: The interpolation/easing preset applied to keyframes.
        value_range: The initial property values at the first and last keyed frames.
    """

    PROPERTY_NAME = "progress"

    def __init__(
        self,
        frame_range: tuple[int, int],
        value_range: tuple[float, float] = (0.0, 1.0),
        *,
        name: str = "Progress",
        preset: FCurvePreset = FCurvePreset.BEZIER,
    ) -> None:
        """Create and keyframe a progress property.

        Args:
            frame_range: Inclusive start and end frames. The start must be before the end.
            value_range: The property values at the start and end frames.
            name: Name of the driver Empty.
            preset: A common interpolation and easing combination supplied by Blender.

        Raises:
            TypeError: If a frame, value, or preset has an unsupported type.
            ValueError: If the frame range or value range is invalid.
        """
        start, stop = frame_range
        if (
            isinstance(start, bool)
            or isinstance(stop, bool)
            or not isinstance(start, int | float)
            or not isinstance(stop, int | float)
        ):
            raise TypeError("Progress track frames must be numbers.")
        if not float(start).is_integer() or not float(stop).is_integer() or start >= stop:
            raise ValueError(f"Frame range must contain increasing integer frames: {frame_range}.")
        if len(value_range) != 2:
            raise ValueError(f"Value range must contain a start and end value: {value_range}.")
        if not all(isinstance(value, int | float) and not isinstance(value, bool) for value in value_range):
            raise TypeError("Progress track values must be numbers.")
        if not isinstance(preset, FCurvePreset):
            raise TypeError(f"Unsupported F-curve preset: {preset!r}.")

        self.value_range = (float(value_range[0]), float(value_range[1]))
        self.driver = Empty(name=name)
        self.driver[self.PROPERTY_NAME] = self.value_range[0]
        self.driver.add_keyframe(self.PROPERTY_NAME, frame=int(start), is_custom=True)
        self.driver[self.PROPERTY_NAME] = self.value_range[1]
        self.driver.add_keyframe(self.PROPERTY_NAME, frame=int(stop), is_custom=True)

        self.fcurve = self._find_fcurve()
        self.preset = preset
        self._apply_preset()
        self._evaluate_current_frame()

    @property
    def value(self) -> float:
        """Return the F-curve value at the current scene frame.

        Unlike the driver's custom property, which Blender updates only after pre-frame handlers run, this is correct
        inside frame-change handlers and after `scene.frame_current` is assigned directly. Use `value_at` to sample
        another frame.

        Returns:
            The F-curve value at the current frame, including its fractional subframe.
        """
        return self.value_at()

    def value_at(self, frame: float | None = None) -> float:
        """Evaluate the property's F-curve at a Blender frame.

        Blender evaluates custom properties after pre-frame handlers, so handlers use this method to sample the
        requested frame without a one-frame delay.

        Args:
            frame: Frame to evaluate, including an optional fractional subframe. Defaults to the current scene frame.

        Returns:
            The F-curve value at `frame`.
        """
        if frame is None:
            scene = bpy.context.scene
            frame = scene.frame_current + scene.frame_subframe
        return float(self.fcurve.evaluate(frame))

    @property
    def start_frame(self) -> float:
        """Return the position of the earliest keyframe.

        Returns:
            The first keyframe's frame position, including fractional positions introduced by direct F-curve edits.
        """
        return self.frame_range[0]

    @property
    def stop_frame(self) -> float:
        """Return the position of the latest keyframe.

        Returns:
            The last keyframe's frame position, including fractional positions introduced by direct F-curve edits.
        """
        return self.frame_range[1]

    def add_keyframe(self, frame: int, value: float) -> None:
        """Add a keyframe to the track and return control to Blender for interpolation.

        Args:
            frame: The integer frame for the new key.
            value: The custom-property value at that frame.

        Raises:
            TypeError: If `frame` is not an integer or `value` is not numeric.
        """
        if isinstance(frame, bool) or not isinstance(frame, int):
            raise TypeError("Keyframe frame must be an integer.")
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise TypeError("Keyframe value must be numeric.")
        self.driver[self.PROPERTY_NAME] = float(value)
        self.driver.add_keyframe(self.PROPERTY_NAME, frame=frame, is_custom=True)
        self.fcurve.update()
        point = min(self.fcurve.keyframe_points, key=lambda keyframe: abs(keyframe.co.x - frame))
        point.interpolation, point.easing = self.preset.value
        self._evaluate_current_frame()

    def _apply_preset(self) -> None:
        """Apply the interpolation preset to all keyframes in the F-curve."""
        for keyframe in self.fcurve.keyframe_points:
            keyframe.interpolation, keyframe.easing = self.preset.value
        self.fcurve.update()

    def _evaluate_current_frame(self) -> None:
        """Evaluate the F-curve at the current frame and update the driver's custom property."""
        scene = bpy.context.scene
        frame = scene.frame_current + scene.frame_subframe
        self.driver[self.PROPERTY_NAME] = self.value_at(frame)

    @property
    def frame_range(self) -> tuple[float, float]:
        """Return the positions of the earliest and latest F-curve keyframes.

        Returns:
            The frame positions of the first and last keyframes.

        Raises:
            RuntimeError: If the F-curve has fewer than two keyframes.
        """
        points = self.fcurve.keyframe_points
        if len(points) < 2:
            raise RuntimeError("A progress track must have at least two keyframes.")
        return points[0].co.x, points[-1].co.x

    def _find_fcurve(self) -> bpy.types.FCurve:
        """Find the Blender F-curve for this driver's custom property.

        Blender 5 stores action curves in channel bags inside layered actions; this searches those bags for the
        property data path.

        Returns:
            The F-curve that animates `PROPERTY_NAME`.

        Raises:
            RuntimeError: If Blender did not create an F-curve for the custom property.
        """
        action = self.driver.object.animation_data.action
        data_path = f'["{self.PROPERTY_NAME}"]'
        for layer in action.layers:
            for strip in layer.strips:
                for slot in action.slots:
                    channelbag = strip.channelbag(slot)
                    if channelbag is not None:
                        for fcurve in channelbag.fcurves:
                            if fcurve.data_path == data_path:
                                return fcurve
        raise RuntimeError(f"Blender did not create an F-curve for {data_path}.")


class Action(ABC):
    """A time window over which a progress value drives some change.

    An action is created with only a duration. It receives its start time when a `Scheduler` places it, and only then
    is its keyframed progress track created. An action can therefore be placed once. Subclasses define what the
    progress value does: `Appearance` (used by `Enter` and `Exit`) drives a reveal and `Callback` calls a function.

    Attributes:
        duration: The length of the window.
        target: The object whose state the action controls, or None if it controls no single object.
    """

    def __init__(
        self,
        duration: TimeInput,
        *,
        target: Object | None = None,
        value_range: tuple[float, float] = (0.0, 1.0),
        name: str = "Action",
        preset: FCurvePreset = FCurvePreset.BEZIER,
    ) -> None:
        """Describe an action without placing it on the timeline.

        Args:
            duration: Positive length of the window, as a `timedelta` or time string.
            target: The object whose state the action controls, if any.
            value_range: The progress values at the start and end of the window.
            name: Name of the driver Empty created on placement.
            preset: Blender's built-in interpolation/easing preset for the progress.

        Raises:
            TypeError: If the duration has an unsupported type.
            ValueError: If the duration is not positive.
        """
        self.duration = as_timedelta(duration)
        if self.duration <= timedelta(0):
            raise ValueError("Animation duration must be positive.")
        self.target = target
        self._value_range = value_range
        self._name = name
        self._preset = preset
        self._track: KeyframedProperty | None = None
        self._start_time: timedelta | None = None

    @property
    def placed(self) -> bool:
        """Return whether a scheduler has placed the action on the timeline."""
        return self._track is not None

    @property
    def track(self) -> KeyframedProperty:
        """Return the keyframed progress track created on placement.

        Raises:
            RuntimeError: If the action has not been placed.
        """
        if self._track is None:
            raise RuntimeError(f"{type(self).__name__} has not been placed on a timeline.")
        return self._track

    @property
    def start_time(self) -> timedelta:
        """Return the elapsed time at which the window starts.

        Raises:
            RuntimeError: If the action has not been placed.
        """
        if self._start_time is None:
            raise RuntimeError(f"{type(self).__name__} has not been placed on a timeline.")
        return self._start_time

    @property
    def end_time(self) -> timedelta:
        """Return the elapsed time at which the window ends.

        Raises:
            RuntimeError: If the action has not been placed.
        """
        return self.start_time + self.duration

    def place(self, start_time: TimeInput) -> None:
        """Start the window at an elapsed time and create its progress track.

        The `Scheduler` calls this; user code normally does not.

        Args:
            start_time: Elapsed time from frame 1.

        Raises:
            RuntimeError: If the action was already placed.
            ValueError: If the window is shorter than the scene's frame resolution.
        """
        if self.placed:
            raise RuntimeError(f"{type(self).__name__} was already placed; create a new action instead.")
        start = as_timedelta(start_time)
        self._track = KeyframedProperty(
            range_to_frames(start, self.duration), self._value_range, name=self._name, preset=self._preset
        )
        self._start_time = start

    @property
    def start_frame(self) -> float:
        """Return the first frame controlled by the track."""
        return self.track.start_frame

    @property
    def stop_frame(self) -> float:
        """Return the last frame controlled by the track."""
        return self.track.stop_frame

    @abstractmethod
    def apply(self, frame: float | None = None) -> None:
        """Apply the action's state at a frame.

        Args:
            frame: Blender frame to evaluate, including an optional fractional subframe. Defaults to the current
                scene frame.
        """

    def invalidate(self) -> None:  # noqa: B027 (an optional hook, so it is not abstract)
        """Discard cached target state before the next application.

        Override this when the action's strategy caches its last output and another action may have changed the same
        target in the meantime.
        """


class Appearance(Action):
    """Apply a keyframed progress value to an object's reveal strategy.

    Values are passed to `Reveal.apply`, which clamps them to [0, 1]. This class does not reverse or reinterpret the
    progress; the value range determines the direction of the appearance.

    Attributes:
        target: The object whose appearance is controlled.
        reveal: The strategy that applies progress to the target.
    """

    target: Object

    def __init__(
        self,
        target: Object,
        duration: TimeInput,
        *,
        value_range: tuple[float, float] = (0.0, 1.0),
        name: str = "Appearance",
        preset: FCurvePreset = FCurvePreset.BEZIER,
        reveal: Reveal | None = None,
    ) -> None:
        """Bind an object's reveal to a progress window.

        Args:
            target: The object whose appearance is controlled.
            duration: Positive length of the window, as a `timedelta` or time string.
            value_range: The reveal progress at the start and end of the window.
            name: Name of the driver Empty created on placement.
            preset: Blender's built-in interpolation/easing preset.
            reveal: The strategy to use. Defaults to the target's `create_reveal()` strategy.

        Raises:
            TypeError: If the duration has an unsupported type.
            ValueError: If the duration is not positive or the reveal is bound to another object.
        """
        super().__init__(duration, target=target, value_range=value_range, name=name, preset=preset)
        if reveal is not None and reveal.target is not target:
            raise ValueError("The reveal is bound to a different object than the action's target.")
        self.reveal = reveal if reveal is not None else target.create_reveal()

    def apply(self, frame: float | None = None) -> None:
        """Apply the reveal state sampled from the track.

        Args:
            frame: Blender frame to evaluate, including an optional fractional subframe. Defaults to the current
                scene frame.
        """
        self.reveal.apply(self.track.value_at(frame))

    def invalidate(self) -> None:
        """Invalidate the reveal's cached state so the next application updates the target."""
        self.reveal.invalidate()


class Enter(Appearance):
    """Animate an object into the scene, defaulting to progress 0 to 1."""

    def __init__(
        self,
        target: Object,
        duration: TimeInput,
        *,
        value_range: tuple[float, float] = (0.0, 1.0),
        name: str = "Enter",
        preset: FCurvePreset = FCurvePreset.BEZIER,
        reveal: Reveal | None = None,
    ) -> None:
        """Create an entry action.

        Args:
            target: The object to bring into the scene.
            duration: Positive animation duration, as a `timedelta` or time string.
            value_range: The reveal progress at the start and end; defaults to (0, 1).
            name: Name of the driver Empty created on placement.
            preset: Blender's built-in interpolation/easing preset.
            reveal: The target's default reveal strategy, or an explicit alternative.

        Raises:
            TypeError: If the duration has an unsupported type.
            ValueError: If the duration is not positive or the reveal belongs to another target.
        """
        super().__init__(target, duration, value_range=value_range, name=name, preset=preset, reveal=reveal)


class Exit(Appearance):
    """Animate an object out of the scene, defaulting to progress 1 to 0."""

    def __init__(
        self,
        target: Object,
        duration: TimeInput,
        *,
        value_range: tuple[float, float] = (1.0, 0.0),
        name: str = "Exit",
        preset: FCurvePreset = FCurvePreset.BEZIER,
        reveal: Reveal | None = None,
    ) -> None:
        """Create an exit action.

        Args:
            target: The object to take out of the scene.
            duration: Positive animation duration, as a `timedelta` or time string.
            value_range: The reveal progress at the start and end; defaults to (1, 0).
            name: Name of the driver Empty created on placement.
            preset: Blender's built-in interpolation/easing preset.
            reveal: The target's default reveal strategy, or an explicit alternative.

        Raises:
            TypeError: If the duration has an unsupported type.
            ValueError: If the duration is not positive or the reveal belongs to another target.
        """
        super().__init__(target, duration, value_range=value_range, name=name, preset=preset, reveal=reveal)


class Callback(Action):
    """Call a function with the progress of a time window.

    The function may declare either or both of these parameters, matched by name:

    - `u`: the eased progress, running over the value range (0 to 1 by default).
    - `t`: the `timedelta` elapsed since the window started, clamped to the window.

    The function is called on each frame inside the window. It is also called once with the final values after the
    window has passed, and once with the initial values when the scene is before it, so the state it draws is correct
    when scrubbing or jumping to any frame. It is not called on other frames outside the window.
    """

    _PARAMETERS = frozenset({"u", "t"})

    def __init__(
        self,
        function: Callable[..., object],
        duration: TimeInput,
        *,
        value_range: tuple[float, float] = (0.0, 1.0),
        name: str = "Callback",
        preset: FCurvePreset = FCurvePreset.BEZIER,
    ) -> None:
        """Describe a callback over a window.

        Args:
            function: Function taking `u`, `t`, or both as parameters, matched by name.
            duration: Positive length of the window, as a `timedelta` or time string.
            value_range: The progress `u` at the start and end of the window.
            name: Name of the driver Empty created on placement.
            preset: Blender's built-in interpolation/easing preset applied to `u`.

        Raises:
            TypeError: If the function has no parameters, or any parameter is not named `u` or `t`.
            ValueError: If the duration is not positive.
        """
        super().__init__(duration, value_range=value_range, name=name, preset=preset)
        parameters = inspect.signature(function).parameters
        if not parameters or not all(
            parameter.kind in (parameter.POSITIONAL_OR_KEYWORD, parameter.KEYWORD_ONLY) and key in self._PARAMETERS
            for key, parameter in parameters.items()
        ):
            raise TypeError(
                f"A callback may only take the parameters 'u' (progress) and 't' (elapsed time): {parameters}."
            )
        self.function = function
        self._parameters = tuple(parameters)
        self._region: int | None = None

    def apply(self, frame: float | None = None) -> None:
        """Call the function if the frame is inside the window or the window's side changed since the last call.

        Args:
            frame: Blender frame to evaluate, including an optional fractional subframe. Defaults to the current
                scene frame.
        """
        if frame is None:
            scene = bpy.context.scene
            frame = scene.frame_current + scene.frame_subframe
        start, stop = self.start_frame, self.stop_frame
        region = -1 if frame < start else 1 if frame > stop else 0
        if region != 0 and region == self._region:
            return
        self._region = region
        values = {
            "u": self.track.value_at(frame),
            "t": from_frame(min(max(frame, start), stop)) - from_frame(start),
        }
        self.function(**{key: values[key] for key in self._parameters})

    def invalidate(self) -> None:
        """Forget which side of the window was last drawn so the next application calls the function."""
        self._region = None
