"""Drives appearance actions from Blender's keyframed custom properties."""

from __future__ import annotations

from collections.abc import Iterable
from typing import ClassVar

import bpy

from anima.animation.action import Action
from anima.animation.updater import Updater


class Scheduler:
    """Apply keyframed actions to targets as the Blender frame changes.

    Actions are grouped by target. At each frame, the latest-starting action whose start frame has been reached
    controls its target; before the first action starts, the earliest-starting action controls it. When control
    switches between actions, the newly selected action is invalidated so it reapplies its state even if its sampled
    value matches a previously applied value.

    Avoid registering competing actions on an object and its descendants; the scheduler tracks each target
    independently and does not resolve hierarchy conflicts.
    """

    _instance: ClassVar[Scheduler | None] = None

    def __init__(self) -> None:
        """Create an empty scheduler.

        Use `Scheduler.instance` for the shared, frame-handler-driven scheduler. A directly constructed scheduler is
        useful when its evaluation is managed explicitly.
        """
        self._by_target: dict[int, list[Action]] = {}
        self._driver: dict[int, Action] = {}

    @classmethod
    def instance(cls) -> Scheduler:
        """Return the shared scheduler, creating and registering it on first use.

        Returns:
            The shared scheduler connected to the shared pre-frame updater.
        """
        if cls._instance is None:
            cls._instance = cls()
            Updater.instance().add_callback(cls._instance._on_frame_change)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Unregister and discard the shared scheduler and its actions.

        This removes the scheduler callback from the shared updater without clearing other registered callbacks. It
        is appropriate when rebuilding a scene so actions bound to the previous scene are not retained.
        """
        if cls._instance is not None:
            Updater.instance().remove_callback(cls._instance._on_frame_change)
            cls._instance.clear()
            cls._instance = None

    @property
    def actions(self) -> list[Action]:
        """Return the registered actions ordered by start frame within each target.

        Returns:
            A new list of all registered actions. The list is grouped by target in registration order; actions for
            each target are sorted by their start frame.
        """
        return [
            action
            for actions in self._by_target.values()
            for action in sorted(actions, key=lambda item: item.start_frame)
        ]

    def add(self, *actions: Action) -> None:
        """Register actions and immediately evaluate their targets at the current scene frame.

        Args:
            *actions: Actions to register. Actions for the same target are sorted by start frame; equal start frames
                retain their registration order.
        """
        targets = set()
        for action in actions:
            key = id(action.target)
            queue = self._by_target.setdefault(key, [])
            queue.append(action)
            queue.sort(key=lambda item: item.start_frame)
            targets.add(key)
        self.evaluate(self.current_frame(), targets)

    def clear(self) -> None:
        """Forget all registered actions and driver selections without changing target state."""
        self._by_target.clear()
        self._driver.clear()

    def evaluate(self, frame: float, targets: Iterable[int] | None = None) -> None:
        """Apply each target's controlling action at a specified Blender frame.

        Args:
            frame: Frame to evaluate, including an optional fractional subframe.
            targets: Optional iterable of target identities (`id(target)`) to update. If omitted, all registered
                targets are evaluated.
        """
        for key in self._by_target if targets is None else targets:
            actions = sorted(self._by_target[key], key=lambda action: action.start_frame)
            controlling = next((action for action in reversed(actions) if action.start_frame <= frame), actions[0])
            if self._driver.get(key) is not controlling:
                controlling.invalidate()
                self._driver[key] = controlling
            controlling.apply(frame)

    def refresh(self) -> None:
        """Evaluate every registered target at the current scene frame.

        Use this after changing the frame without calling Blender's `frame_set`, which is what normally invokes frame
        handlers.
        """
        self.evaluate(self.current_frame())

    @staticmethod
    def current_frame() -> float:
        """Return the current scene frame, including its fractional subframe.

        Returns:
            The active scene's frame position as a float.
        """
        scene = bpy.context.scene
        return scene.frame_current + scene.frame_subframe

    def _on_frame_change(self) -> None:
        """Evaluate all actions for a Blender pre-frame-change event."""
        self.refresh()


def play(*actions: Action) -> None:
    """Register actions with the shared scheduler.

    Actions are applied immediately at the current frame and then reevaluated whenever Blender changes frames.

    Args:
        *actions: Actions to register.
    """
    Scheduler.instance().add(*actions)
