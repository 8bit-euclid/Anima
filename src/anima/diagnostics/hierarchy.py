"""Consistency checks between the Anima object tree and the Blender object tree."""

from __future__ import annotations

from collections.abc import Collection, Iterable

import bpy

from anima.primitives.object import Object

# Blender object types that are never wrapped by an Anima object.
_UNWRAPPED_TYPES = {"CAMERA", "LIGHT"}


def _is_alive(obj: Object) -> bool:
    """Whether the wrapped Blender object still exists (tests and scripts may delete it)."""
    try:
        return obj.object is not None and obj.object.name in bpy.data.objects
    except ReferenceError:
        return False


def check_hierarchy(*, allowed_roots: Iterable[Object] = (), ignore_names: Collection[str] = ()) -> list[str]:
    """Compare the Anima object tree with the Blender object tree.

    The following are reported:

    * An Anima object whose Blender parent differs from its Anima parent's Blender object.
    * A child listed by a parent that does not point back to it.
    * A Blender object in the scene that no Anima object wraps and that is not a bevel profile, camera or
      light (a stray).
    * A top-level Anima object that is not in `allowed_roots` (only when `allowed_roots` is non-empty).

    Args:
        allowed_roots: The objects that may legitimately sit at the top level. If empty, root objects are not
            checked.
        ignore_names: Names of Blender objects to skip in the stray check.

    Returns:
        A list of human-readable problems; empty if the trees are consistent.
    """
    problems: list[str] = []
    objects = [o for o in Object._registry if _is_alive(o)]
    wrapped = {o.object.as_pointer() for o in objects if o.object is not None}
    roots = list(allowed_roots)

    for obj in objects:
        bl = obj.object
        if obj.parent is not None and not _is_alive(obj.parent):  # Parent was deleted from Blender.
            continue
        expected = obj.parent.object if obj.parent is not None else None
        if bl.parent != expected:
            actual = bl.parent.name if bl.parent else None
            wanted = expected.name if expected else None
            problems.append(f"{bl.name}: Blender parent is {actual!r} but the Anima parent is {wanted!r}.")
        for child in obj.children:
            if child.parent is not obj:
                problems.append(f"{child.name}: listed as a child of {obj.name} but its parent is different.")
        if roots and obj.parent is None and not any(obj is r for r in roots):
            problems.append(f"{bl.name}: top-level object that is not an allowed root.")

    profiles = {
        o.object.data.bevel_object.as_pointer()
        for o in objects
        if o.object is not None and getattr(o.object.data, "bevel_object", None) is not None
    }
    for bl in bpy.data.objects:
        if bl.type in _UNWRAPPED_TYPES or bl.name in ignore_names:
            continue
        if bl.as_pointer() not in wrapped and bl.as_pointer() not in profiles:
            problems.append(f"{bl.name}: Blender object not wrapped by any Anima object.")

    return problems


def assert_hierarchy(*, allowed_roots: Iterable[Object] = (), ignore_names: Collection[str] = ()) -> None:
    """Raise if the Anima and Blender object trees disagree. See `check_hierarchy`.

    Args:
        allowed_roots: The objects that may legitimately sit at the top level.
        ignore_names: Names of Blender objects to skip in the stray check.

    Raises:
        AssertionError: If any problem is found; the message lists them all.
    """
    problems = check_hierarchy(allowed_roots=allowed_roots, ignore_names=ignore_names)
    assert not problems, "Inconsistent object hierarchy:\n  " + "\n  ".join(problems)
