"""Width-wise opacity and bump profiles for curve materials."""

from __future__ import annotations

import math
from collections.abc import Callable

import bpy

from anima.materials.material import get_material_opacity
from anima.materials.texture import TEXTURE_GROUP_NODE

PROFILE_PREFIX = "anima_curve_profile_"
PROFILE_IMAGE = PROFILE_PREFIX + "image"
PROFILE_ALPHA = PROFILE_PREFIX + "alpha"
PROFILE_BUMP = PROFILE_PREFIX + "bump"
PROFILE_SOURCE = PROFILE_PREFIX + "source"
PROFILE_UV = "AnimaCurveProfile"

ProfileSamples = tuple[tuple[float, float], ...]


def sample_profile(
    height: Callable[[float], float] | None,
    opacity: Callable[[float], float] | None,
    samples: int,
) -> ProfileSamples:
    """Sample height and opacity uniformly across the normalized curve width.

    Args:
        height: Function returning a signed height in scene units, or None for zero height.
        opacity: Function returning opacity in [0, 1], or None for full opacity.
        samples: Number of samples, including both edges; must be at least two.

    Returns:
        Height and opacity pairs ordered from the left edge to the right edge.

    Raises:
        ValueError: If both functions are None, the sample count is invalid, a height
            is not finite, or an opacity is not finite or outside [0, 1].
    """
    if height is None and opacity is None:
        raise ValueError("Provide a height or opacity profile.")
    if isinstance(samples, bool) or not isinstance(samples, int) or samples < 2:
        raise ValueError("samples must be an integer of at least 2.")
    values = []
    for i in range(samples):
        u = i / (samples - 1)
        h = float(height(u)) if height is not None else 0.0
        a = float(opacity(u)) if opacity is not None else 1.0
        if not math.isfinite(h) or not math.isfinite(a) or not 0.0 <= a <= 1.0:
            raise ValueError("Profile heights must be finite and opacity must be finite and in [0, 1].")
        values.append((h, a))
    return tuple(values)


def create_profile_image(samples: ProfileSamples) -> bpy.types.Image:
    """Pack sampled height and opacity into a floating-point image.

    The red and green channels hold height and opacity respectively. Packing the
    image into the Blender file preserves the profile when the scene is saved.

    Args:
        samples: Height and opacity pairs in width order.

    Returns:
        The packed one-row image.
    """
    image = bpy.data.images.new("AnimaCurveProfile", width=len(samples), height=1, float_buffer=True, alpha=True)
    image.colorspace_settings.name = "Non-Color"
    image.pixels = [channel for height, opacity in samples for channel in (height, opacity, 0.0, 1.0)]
    image.file_format = "OPEN_EXR"
    image.pack()
    image[PROFILE_PREFIX + "owned"] = True
    return image


def validate_curve_profile(mat: bpy.types.Material) -> None:
    """Reject materials whose custom shader links cannot be preserved.

    Args:
        mat: Material to validate before installing a profile.

    Raises:
        ValueError: If the material lacks a Principled BSDF or its Alpha or Normal
            input has a link other than the existing Anima texture or profile link.
    """
    tree = mat.node_tree
    if tree is None or (bsdf := tree.nodes.get("Principled BSDF")) is None:
        raise ValueError(f"Material {mat.name!r} must have a Principled BSDF.")
    for socket, allowed in (
        ("Alpha", {PROFILE_ALPHA, TEXTURE_GROUP_NODE}),
        ("Normal", {PROFILE_BUMP, TEXTURE_GROUP_NODE}),
    ):
        if any(link.from_node.name not in allowed for link in bsdf.inputs[socket].links):
            raise ValueError(f"Cannot replace a custom {socket} link on material {mat.name!r}.")


def _release_image(image: bpy.types.Image | None) -> None:
    if image is not None and image.get(PROFILE_PREFIX + "owned") and image.users == 0:
        bpy.data.images.remove(image)


def apply_curve_profile(mat: bpy.types.Material, image: bpy.types.Image) -> None:
    """Apply a width profile to a material's Principled BSDF.

    The image's red channel supplies signed bump height and its green channel
    supplies opacity. The profile multiplies the material or texture opacity and
    applies bump on top of any texture normal. Reapplying it replaces the image
    while retaining the existing profile nodes.

    Args:
        mat: Material to modify. Shared materials affect all objects using them.
        image: Packed profile image produced by ``create_profile_image``.

    Raises:
        ValueError: If the material lacks a Principled BSDF or has a custom
            Alpha or Normal link that would be replaced.
    """
    validate_curve_profile(mat)
    tree = mat.node_tree
    nodes, links = tree.nodes, tree.links
    old_image = nodes.get(PROFILE_IMAGE)
    if old_image is not None:
        previous = old_image.image
        old_image.image = image
        _release_image(previous)
        nodes[PROFILE_PREFIX + "uv"].uv_map = PROFILE_UV if mat.get(PROFILE_SOURCE) else "UVMap"
        scale = nodes[PROFILE_PREFIX + "scale"]
        scale.inputs[1].default_value = (image.size[0] - 1) / image.size[0]
        scale.inputs[2].default_value = 0.5 / image.size[0]
        return

    uv = nodes.new("ShaderNodeUVMap")
    uv.name = PROFILE_PREFIX + "uv"
    uv.uv_map = PROFILE_UV if mat.get(PROFILE_SOURCE) else "UVMap"
    separate = nodes.new("ShaderNodeSeparateXYZ")
    separate.name = PROFILE_PREFIX + "coordinate"
    links.new(uv.outputs["UV"], separate.inputs["Vector"])

    # Curve UV Y runs across the width; map its endpoints to the first and last pixel centers.
    scale = nodes.new("ShaderNodeMath")
    scale.name = PROFILE_PREFIX + "scale"
    scale.operation = "MULTIPLY_ADD"
    scale.inputs[1].default_value = (image.size[0] - 1) / image.size[0]
    scale.inputs[2].default_value = 0.5 / image.size[0]
    links.new(separate.outputs["Y"], scale.inputs[0])
    coords = nodes.new("ShaderNodeCombineXYZ")
    coords.name = PROFILE_PREFIX + "image_coordinate"
    coords.inputs["Y"].default_value = 0.5
    links.new(scale.outputs[0], coords.inputs["X"])
    tex = nodes.new("ShaderNodeTexImage")
    tex.name = PROFILE_IMAGE
    tex.image = image

    # Endcaps can extend beyond the curve width; keep the nearest edge value there.
    tex.extension = "EXTEND"
    tex.interpolation = "Linear"
    links.new(coords.outputs[0], tex.inputs["Vector"])
    channels = nodes.new("ShaderNodeSeparateColor")
    channels.name = PROFILE_PREFIX + "channels"
    links.new(tex.outputs["Color"], channels.inputs["Color"])

    # Green modulates overall opacity; red adds profile relief to the existing normal.
    alpha = nodes.new("ShaderNodeMath")
    alpha.name = PROFILE_ALPHA
    alpha.operation = "MULTIPLY"
    alpha.inputs[0].default_value = get_material_opacity(mat)
    links.new(channels.outputs["Green"], alpha.inputs[1])
    bump = nodes.new("ShaderNodeBump")
    bump.name = PROFILE_BUMP
    bump.inputs["Strength"].default_value = 1.0
    bump.inputs["Distance"].default_value = 1.0
    links.new(channels.outputs["Red"], bump.inputs["Height"])
    refresh_curve_profile(mat)


def refresh_curve_profile(mat: bpy.types.Material) -> None:
    """Reconnect a profile after the texture group changes.

    Texture alpha feeds the profile's opacity multiplier, and the texture normal
    feeds its bump node. Without texture alpha, the material opacity is used.
    Does nothing if the material has no complete profile node setup.

    Args:
        mat: Material whose profile links should be refreshed.
    """
    tree = mat.node_tree
    if tree is None:
        return
    nodes, links = tree.nodes, tree.links
    alpha, bump = nodes.get(PROFILE_ALPHA), nodes.get(PROFILE_BUMP)
    bsdf = nodes.get("Principled BSDF")
    if alpha is None or bump is None or bsdf is None:
        return
    texture = nodes.get(TEXTURE_GROUP_NODE)

    # Texture alpha already includes material opacity, so it replaces rather than multiplies the fallback.
    for name, target in (("Alpha", alpha.inputs[0]), ("Normal", bump.inputs["Normal"])):
        for link in list(target.links):
            links.remove(link)
        if texture is not None and name in texture.outputs:
            links.new(texture.outputs[name], target)
    alpha.inputs[0].default_value = get_material_opacity(mat)
    links.new(alpha.outputs[0], bsdf.inputs["Alpha"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


def set_curve_profile_opacity(mat: bpy.types.Material, opacity: float) -> None:
    """Update the profile's scalar opacity fallback.

    A linked texture alpha takes precedence over this value. Does nothing if
    the material has no profile opacity node.

    Args:
        mat: Material whose profile opacity should be updated.
        opacity: Overall material opacity.
    """
    if mat.node_tree is not None:
        node = mat.node_tree.nodes.get(PROFILE_ALPHA)
        if node is not None:
            node.inputs[0].default_value = opacity


def remove_curve_profile(mat: bpy.types.Material) -> None:
    """Remove profile nodes and restore any texture alpha and normal links.

    An owned profile image is removed only when it has no remaining users.
    Does nothing if the material has no profile image node.

    Args:
        mat: Material from which to remove the profile.
    """
    tree = mat.node_tree
    if tree is None or (node := tree.nodes.get(PROFILE_IMAGE)) is None:
        return
    image = node.image
    for node in [node for node in tree.nodes if node.name.startswith(PROFILE_PREFIX)]:
        tree.nodes.remove(node)
    _release_image(image)
    bsdf = tree.nodes.get("Principled BSDF")
    texture = tree.nodes.get(TEXTURE_GROUP_NODE)
    if bsdf is not None and texture is not None:
        for name in ("Alpha", "Normal"):
            if name in texture.outputs:
                tree.links.new(texture.outputs[name], bsdf.inputs[name])
