"""Schedule actions on Blender's frame-change timeline."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import timedelta
from typing import ClassVar, TypeVar, overload

import bpy

from anima.animation.action import Action, FCurvePreset
from anima.animation.effects import Callback, Effect
from anima.animation.timeline import TimeInput, as_timedelta, to_frame

F = TypeVar("F", bound=Callable[..., object])


class Scheduler:
    """Place actions one after another on a single shared animation timeline.

    Constructing the class always returns the shared scheduler. Users specify durations only; the scheduler keeps a
    cursor that starts at zero and places each action where the previous one ended:

    - `add` wraps an effect in an action, places it at the cursor, and returns the action.
    - `add_action` places one action at the cursor and moves the cursor to its end.
    - `add_actions` places several actions at the same cursor, so they run in parallel, and moves the cursor to the
      end of the longest.
    - Passing `with_previous=True` instead starts the placement together with the previous one. The cursor then
      moves to whichever ends last, so the next default placement waits for everything.
    - `wait` moves the cursor without placing anything.
    - `end_time` reports where the cursor is, which is the end of everything scheduled.

    Actions are grouped by target. The latest-starting action whose start frame has been reached controls its target;
    before the first action starts, the earliest-starting action controls it. Avoid competing actions on an object
    and its descendants because the scheduler does not resolve hierarchy conflicts. Actions without a target, such as
    callbacks, are independent of one another.
    """

    _instance: ClassVar[Scheduler | None] = None

    def __new__(cls) -> Scheduler:
        """Return the shared scheduler, allocating it only on first construction."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Register the scheduler's Blender frame handler once."""
        if getattr(self, "_initialized", False):
            return
        self._by_target: dict[int, list[Action]] = {}
        self._driver: dict[int, Action] = {}
        self._cursor = timedelta(0)
        self._previous_start = timedelta(0)
        bpy.app.handlers.frame_change_pre.append(_dispatch_frame_change)
        self._initialized = True

    @property
    def actions(self) -> list[Action]:
        """Return the registered actions ordered by start time within each target.

        Returns:
            A new list of all registered actions. The list is grouped by target in registration order; actions for
            each target are sorted by their start time.
        """
        return [
            action
            for actions in self._by_target.values()
            for action in sorted(actions, key=lambda item: item.start_frame)
        ]

    @property
    def end_time(self) -> timedelta:
        """Return the elapsed time at which everything scheduled so far has finished, including waits."""
        return self._cursor

    def add_action(self, action: Action, *, with_previous: bool = False) -> None:
        """Place one action, apply it at the current scene frame, and advance the cursor.

        Args:
            action: Action to place.
            with_previous: Start together with the previous placement instead of at the cursor.

        Raises:
            RuntimeError: If the action was already placed.
        """
        self.add_actions(action, with_previous=with_previous)

    def add(
        self,
        effect: Effect,
        duration: TimeInput,
        *,
        value_range: tuple[float, float] = (0.0, 1.0),
        name: str = "Action",
        preset: FCurvePreset = FCurvePreset.BEZIER,
        with_previous: bool = False,
    ) -> Action:
        """Wrap an effect in an action and place it at the cursor.

        Args:
            effect: Effect to apply.
            duration: Positive length of the window, in seconds, as a `timedelta`, or as a time string.
            value_range: The progress values at the start and end of the window.
            name: Name of the driver Empty created on placement.
            preset: Blender's built-in interpolation/easing preset for the progress.
            with_previous: Start together with the previous placement instead of at the cursor.

        Returns:
            The placed action.
        """
        action = Action(effect, duration, value_range=value_range, name=name, preset=preset)
        self.add_action(action, with_previous=with_previous)
        return action

    def add_actions(self, *actions: Action, with_previous: bool = False) -> None:
        """Place actions in parallel, then advance the cursor to the end of the latest-ending one.

        Each action is applied at the current scene frame once placed.

        Args:
            *actions: Actions to place. Actions for the same target are sorted by start frame; equal start frames
                retain their registration order.
            with_previous: Start together with the previous placement instead of at the cursor. With nothing
                placed yet, this starts at time zero.

        Raises:
            RuntimeError: If any action was already placed. Nothing is placed in that case.
        """
        if any(action.placed for action in actions):
            raise RuntimeError("An action can be placed only once; create a new action instead.")
        start = self._previous_start if with_previous else self._cursor
        keys = []
        for action in actions:
            action.place(start)
            key = id(action.target) if action.target is not None else id(action)
            queue = self._by_target.setdefault(key, [])
            queue.append(action)
            queue.sort(key=lambda item: item.start_frame)
            keys.append(key)
        if actions:
            self._previous_start = start
            self._cursor = max(self._cursor, start + max(action.duration for action in actions))
        self._evaluate_actions(self._current_frame(), keys)

    @overload
    def add_callback(
        self,
        function: F,
        /,
        *,
        duration: TimeInput,
        value_range: tuple[float, float] = ...,
        name: str = ...,
        preset: FCurvePreset = ...,
        with_previous: bool = ...,
    ) -> F: ...

    @overload
    def add_callback(
        self,
        function: None = None,
        /,
        *,
        duration: TimeInput,
        value_range: tuple[float, float] = ...,
        name: str = ...,
        preset: FCurvePreset = ...,
        with_previous: bool = ...,
    ) -> Callable[[F], F]: ...

    def add_callback(
        self,
        function: Callable[..., object] | None = None,
        /,
        *,
        duration: TimeInput,
        value_range: tuple[float, float] = (0.0, 1.0),
        name: str = "Callback",
        preset: FCurvePreset = FCurvePreset.BEZIER,
        with_previous: bool = False,
    ) -> Callable[..., object] | Callable[[F], F]:
        """Place a callback at the cursor; shorthand for `add(Callback(...), duration)`.

        It can be used directly or as a decorator:

            scheduler.add_callback(draw, duration=2)

            @scheduler.add_callback(duration=2)
            def draw(u): ...

        See `Callback` for the parameters the function may take and when it is called.

        Args:
            function: Function taking `u` (progress), `t` (elapsed time), or both. Omit it to use the decorator form.
            duration: Positive length of the window, in seconds, as a `timedelta`, or as a time string.
            value_range: The progress `u` at the start and end of the window.
            name: Name of the driver Empty.
            preset: Blender's built-in interpolation/easing preset applied to `u`.
            with_previous: Start together with the previous placement instead of at the cursor.

        Returns:
            The function itself, or a decorator that registers a function and returns it.

        Raises:
            TypeError: If the function takes parameters other than `u` and `t`.
            ValueError: If the duration is not positive.
        """

        def register(target: Callable[..., object]) -> Callable[..., object]:
            self.add(
                Callback(target),
                duration,
                value_range=value_range,
                name=name,
                preset=preset,
                with_previous=with_previous,
            )
            return target

        return register if function is None else register(function)

    def wait(self, duration: TimeInput) -> None:
        """Advance the cursor without placing anything.

        Args:
            duration: Non-negative length of the pause, in seconds, as a `timedelta`, or as a time string.

        Raises:
            TypeError: If the duration has an unsupported type.
            ValueError: If the duration is negative.
        """
        self._cursor += as_timedelta(duration)

    def reset(self) -> None:
        """Forget all actions and return the cursor and previous start to zero, without changing the state of any target."""
        self._by_target.clear()
        self._driver.clear()
        self._cursor = timedelta(0)
        self._previous_start = timedelta(0)

    def evaluate(self, at: TimeInput) -> None:
        """Evaluate every action at an elapsed animation time.

        Args:
            at: Elapsed time from frame 1, in seconds, as a `timedelta`, or as an accepted time string. It is rounded
                to the nearest frame at the active scene's frame rate.
        """
        self._evaluate_actions(to_frame(at))

    def refresh(self) -> None:
        """Re-apply every action at the active scene's current frame, discarding all cached state."""
        for actions in self._by_target.values():
            for action in actions:
                action.invalidate()
        self._evaluate_actions(self._current_frame())

    def _evaluate_actions(self, frame: float, targets: Iterable[int] | None = None) -> None:
        """Apply the controlling action for each selected target."""
        keys = self._by_target if targets is None else targets
        for key in keys:
            actions = self._by_target.get(key)
            if not actions:
                continue
            controlling = next((action for action in reversed(actions) if action.start_frame <= frame), actions[0])
            if self._driver.get(key) is not controlling:
                controlling.invalidate()
                self._driver[key] = controlling
            controlling.apply(frame)

    @staticmethod
    def _current_frame() -> float:
        """Return the active scene's current Blender frame including its subframe."""
        scene = bpy.context.scene
        return scene.frame_current + scene.frame_subframe

    def _on_frame_change(self, scene: bpy.types.Scene) -> None:
        """Evaluate actions for a Blender pre-frame-change event."""
        self._evaluate_actions(scene.frame_current + scene.frame_subframe)


@bpy.app.handlers.persistent
def _dispatch_frame_change(scene: bpy.types.Scene, *_: object) -> None:
    """Bridge Blender's pre-frame handler to the shared scheduler.

    Args:
        scene: The scene whose frame is about to be evaluated.
        *_: Additional Blender handler arguments, ignored by the scheduler.
    """
    scheduler = Scheduler._instance
    if scheduler is not None:
        scheduler._on_frame_change(scene)
