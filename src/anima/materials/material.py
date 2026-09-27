import bpy
from mathutils import Color

RGB = tuple[float, float, float]
RGBA = tuple[float, float, float, float]


def to_rgba(color: RGB | RGBA) -> RGBA:
    """Normalize a color to an (r, g, b, a) tuple, defaulting alpha to 1.0 if omitted.

    Args:
        color: An (r, g, b) or (r, g, b, a) tuple of floats in [0, 1].

    Returns:
        The (r, g, b, a) equivalent of the given color.
    """
    return tuple(color) if len(color) == 4 else (*color, 1.0)


def srgb_to_linear_rgba(color: RGB | RGBA) -> RGBA:
    """Convert an sRGB color to linear color space, preserving alpha.

    Args:
        color: An (r, g, b) or (r, g, b, a) tuple of floats in [0, 1].

    Returns:
        The (r, g, b, a) equivalent of the given color in linear color space.
    """
    rgba = to_rgba(color)
    linear = Color(rgba[:3]).from_srgb_to_scene_linear()
    return (*linear, rgba[3])


def create_color_material(name: str, color: RGB | RGBA) -> bpy.types.Material:
    """Get or create a material with the given name and set it to the given color.

    Args:
        name: The name of the material.
        color: An (r, g, b) or (r, g, b, a) tuple of floats in [0, 1]. Alpha defaults to 1.0 if omitted.

    Returns:
        The material with the given name, set to the given color.
    """
    color = to_rgba(color)
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True

    mat.diffuse_color = color  # Used for solid shading in the viewport.
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = color

    return mat


def get_material_color(mat: bpy.types.Material) -> RGBA:
    """Get the RGBA color currently assigned to a material.

    Args:
        mat: The material to query.

    Returns:
        The (r, g, b, a) color of the material.
    """
    return tuple(mat.diffuse_color)


def create_area_light(name: str = "Key Light"):
    """Create an area light in the scene.

    Args:
        name: The name of the area light object.

    Returns:
        The created area light object.
    """
    light_data = bpy.data.lights.new(name, type="AREA")
    light_data.energy = 500
    light_data.shape = "DISK"
    light_data.size = 5

    light = bpy.data.objects.new(name, light_data)
    bpy.context.collection.objects.link(light)

    light.location = (0, 0, 5)
    return light
