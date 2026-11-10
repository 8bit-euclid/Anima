"""Scene-scoped access to visual profiles and background surfaces."""

import json
from dataclasses import asdict
from typing import TYPE_CHECKING

import bpy

from anima.scene.profile import FRAME_16X9_V1, VisualProfile

if TYPE_CHECKING:
    from anima.primitives.object import Object

_backgrounds: dict[bpy.types.Scene, "Object"] = {}
_PROFILE_KEY = "anima_visual_profile"


def set_profile(profile: VisualProfile) -> None:
    """Set the active scene's visual profile.

    Existing objects and render settings are not reconfigured; select a profile
    before building the scene. The setting persists when objects are cleared.
    """
    if not isinstance(profile, VisualProfile):
        raise TypeError("profile must be a VisualProfile.")
    bpy.context.scene[_PROFILE_KEY] = json.dumps(asdict(profile))


def get_profile() -> VisualProfile:
    """Return the active scene's profile, or the default if none was selected."""
    data = bpy.context.scene.get(_PROFILE_KEY)
    if data is None:
        return FRAME_16X9_V1
    values = json.loads(data)
    for key in ("preview_resolution", "master_resolution", "sun_rotation"):
        values[key] = tuple(values[key])
    return VisualProfile(**values)


def reset_profile() -> None:
    """Restore the active scene's default profile without changing existing objects."""
    scene = bpy.context.scene
    if _PROFILE_KEY in scene:
        del scene[_PROFILE_KEY]


def register_background(background: "Object") -> None:
    """Register a background belonging to the active Blender scene."""
    scene = bpy.context.scene
    if scene.objects.get(background.object.name) != background.object:
        raise ValueError("The background must belong to the active scene.")
    _backgrounds[scene] = background


def get_background() -> "Object":
    """Return the active scene's background, rejecting missing or deleted objects.

    Raises:
        RuntimeError: If no live background is registered for the active scene.
    """
    scene = bpy.context.scene
    background = _backgrounds.get(scene)
    if background is not None:
        try:
            obj = background.object
            if scene.objects.get(obj.name) == obj:
                return background
        except ReferenceError:
            pass
        _backgrounds.pop(scene, None)
    raise RuntimeError("No active background is registered for this scene.")


def clear_backgrounds() -> None:
    """Forget all backgrounds when all Blender objects are cleared."""
    _backgrounds.clear()
