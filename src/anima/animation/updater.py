"""A shared dispatcher for Blender's pre-frame-change handlers."""

from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar

import bpy


class Updater:
    """Dispatch callbacks from Blender's shared pre-frame-change handler.

    There is one updater instance. Subscribers share its handler registration, so creating the updater does not clear
    Blender's handler list and registering one callback does not replace other subscribers.
    """

    _instance: ClassVar[Updater | None] = None
    """The singleton instance, created on the first call to `instance` or `Updater()`."""

    def __new__(cls) -> Updater:
        """Return the singleton object, allocating it only on first construction."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Register the singleton's Blender handler once."""
        if getattr(self, "_initialized", False):
            return
        self._functions: list[Callable[[], None]] = []
        bpy.app.handlers.frame_change_pre.append(_dispatch_frame_change)
        self._initialized = True

    @classmethod
    def instance(cls) -> Updater:
        """Return the single shared updater instance.

        Returns:
            The updater that dispatches callbacks before each frame is evaluated.
        """
        return cls()

    def add_callback(self, function: Callable[[], None]) -> None:
        """Register a callback for pre-frame-change events.

        The same callback is registered only once. It is called with no arguments; read the new frame from
        `bpy.context.scene`.

        Args:
            function: Zero-argument callback to invoke before Blender evaluates a frame.
        """
        if function not in self._functions:
            self._functions.append(function)

    def remove_callback(self, function: Callable[[], None]) -> None:
        """Unregister a callback without affecting other subscribers.

        Args:
            function: Callback to remove. If it is not registered, this method does nothing.
        """
        if function in self._functions:
            self._functions.remove(function)

    def _dispatch(self) -> None:
        """Invoke a snapshot of registered callbacks.

        Iterating over a snapshot allows callbacks to add or remove subscribers without changing the current
        dispatch pass.
        """
        for function in tuple(self._functions):
            function()


@bpy.app.handlers.persistent
def _dispatch_frame_change(scene: bpy.types.Scene, *_: object) -> None:
    """Bridge Blender's pre-frame handler to the singleton, if it has been created.

    The persistent handler survives file loads; the updater instance is consulted at call time so it need not be
    created unless a feature subscribes to frame changes.

    Args:
        scene: The scene whose frame is about to be evaluated; unused, since callbacks read the active scene.
        *_: Additional Blender handler arguments, ignored by the dispatcher.
    """
    updater = Updater._instance
    if updater is not None:
        updater._dispatch()
