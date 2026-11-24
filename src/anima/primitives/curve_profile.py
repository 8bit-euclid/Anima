"""Apply width profiles across curve hierarchies."""

from __future__ import annotations

from collections.abc import Callable, Iterator

import bpy

from anima.materials.curve_profile import (
    PROFILE_IMAGE,
    PROFILE_SOURCE,
    apply_curve_profile,
    create_profile_image,
    remove_curve_profile,
    sample_profile,
    validate_curve_profile,
)
from anima.materials.material import create_material

from .curves import Curve
from .endcaps import Endcap
from .object import Object


def _parts(curve: Curve) -> Iterator[tuple[Curve | Endcap, Curve]]:
    yield curve, curve
    for child in curve.children:
        if isinstance(child, Curve):
            yield from _parts(child)
        elif isinstance(child, Endcap):
            yield child, curve


def profile_image(obj: Object) -> bpy.types.Image | None:
    """Return the profile image currently assigned to the object's material."""
    if not obj._has_data() or not obj.object.data.materials:
        return None
    mat = obj.object.data.materials[0]
    if mat.node_tree is None:
        return None
    node = mat.node_tree.nodes.get(PROFILE_IMAGE)
    if node is None:
        return None
    if node.image is None:
        raise RuntimeError(f"Curve profile on material {mat.name!r} has no image.")
    return node.image


def apply_profile_material(obj: Object, image: bpy.types.Image) -> None:
    """Apply a profile image to the object's first material."""
    if obj._has_data():
        materials = obj.object.data.materials
        if not materials:
            materials.append(create_material(f"{obj.name}_material"))
        apply_curve_profile(materials[0], image)


def apply_endcap_profile(curve: Curve, endcap: Endcap) -> None:
    """Associate an endcap's material with its curve's profile."""
    curve_materials = curve.object.data.materials
    if not curve_materials:
        curve_materials.append(create_material(f"{curve.name}_material"))
    endcap_materials = endcap.object.data.materials
    if not endcap_materials:
        endcap_materials.append(create_material(f"{endcap.name}_material"))
    source, material = curve_materials[0], endcap_materials[0]
    if source != material:
        material[PROFILE_SOURCE] = source
    endcap._update_profile_uv(curve.width, is_start=endcap is curve.attachment_0, shared_material=source == material)
    if (image := profile_image(curve)) is not None:
        apply_curve_profile(material, image)


def _related_materials(materials: list[bpy.types.Material]) -> list[bpy.types.Material]:
    """Include materials subscribed to the supplied materials' profiles."""
    dependents: dict[bpy.types.Material, list[bpy.types.Material]] = {}
    for material in bpy.data.materials:
        source = material.get(PROFILE_SOURCE)
        if material.users and isinstance(source, bpy.types.Material):
            dependents.setdefault(source, []).append(material)

    related = list(dict.fromkeys(materials))
    seen = set(related)
    for material in related:
        for dependent in dependents.get(material, ()):
            if dependent not in seen:
                related.append(dependent)
                seen.add(dependent)
    return related


def set_width_profile(
    curve: Curve,
    height: Callable[[float], float] | None,
    opacity: Callable[[float], float] | None,
    samples: int,
    *,
    width_fraction: float = 1.0,
) -> None:
    """Apply a sampled profile over the rightmost fraction of a curve hierarchy."""
    values = sample_profile(height, opacity, samples)
    parts = list(_parts(curve))
    materials = _related_materials(
        [part.object.data.materials[0] for part, _ in parts if part._has_data() and part.object.data.materials]
    )
    for material in materials:
        validate_curve_profile(material)

    image = create_profile_image(values, width_fraction=width_fraction)
    for part, owner in parts:
        if isinstance(part, Curve):
            part._apply_width_profile(image)
        else:
            apply_endcap_profile(owner, part)
    for material in materials:
        apply_curve_profile(material, image)


def clear_width_profile(curve: Curve) -> None:
    """Remove profile nodes from a curve hierarchy's materials."""
    materials = _related_materials(
        [part.object.data.materials[0] for part, _ in _parts(curve) if part._has_data() and part.object.data.materials]
    )
    for material in materials:
        remove_curve_profile(material)
