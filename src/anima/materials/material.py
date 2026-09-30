import bpy
from mathutils import Color

RGB8 = tuple[int, int, int]
RGBA8 = tuple[int, int, int, int]
RGB = tuple[float, float, float]
RGBA = tuple[float, float, float, float]
HEX = str
PALETTE = dict[str, RGB | RGBA | HEX]

PALETTES: dict[str, PALETTE] = {
    "byrne_euclid": {
        "red1": "#D84227",
        "red2": "#C51307",
        "blue1": "#265999",
        "blue2": "#04518C",
        "yellow1": "#F3B319",
        "yellow2": "#F2A922",
        "black": "#000000",
        "paper": "#FEF3D7",
    },
    "rougeux_euclid": {
        "red": "#D90416",
        "blue": "#04668C",
        "yellow": "#FFC001",
        "black": "#000000",
        "paper": "#FEF3D7",
    },
}


def get_palette_color(palette: str, color_name: str) -> RGB | RGBA:
    """Look up a reusable named color from a named palette.

    Args:
        palette: The palette name.
        color_name: The color name within that palette.

    Returns:
        The RGB or RGBA tuple assigned to the requested palette color.

    Raises:
        KeyError: If the palette or color name does not exist.
    """
    color = PALETTES[palette][color_name]
    if isinstance(color, str):
        if _is_hex_str(color):
            color = hex_to_rgb(color)
        else:
            raise TypeError("Expected a HEX color string")
    else:
        if _is_rgb8_tuple(color):
            color = rgb8_to_rgb(color)
        elif _is_rgba8_tuple(color):
            color = rgba8_to_rgba(color)
        elif not (
            _is_rgb_tuple(color, min_value=0.0, max_value=1.0) or _is_rgba_tuple(color, min_value=0.0, max_value=1.0)
        ):
            raise TypeError("Expected an RGB or RGBA color tuple")
    return color


def list_palettes() -> dict[str, PALETTE]:
    """Return the available named palettes.

    Returns:
        A dictionary mapping palette names to their corresponding color definitions.
    """
    return PALETTES


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

    mat.use_nodes = True
    mat.diffuse_color = color  # Used for solid shading in the viewport.
    if mat.node_tree is not None:
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf is not None and "Base Color" in bsdf.inputs:
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


def to_rgba(color: RGB | RGBA | HEX) -> RGBA:
    """Normalize a color to an (r, g, b, a) float tuple, defaulting alpha to 1.0 if omitted.

    Args:
        color: An (r, g, b) or (r, g, b, a) tuple of floats in [0, 1], an 8-bit integer tuple,
            or a HEX color string.

    Returns:
        The (r, g, b, a) equivalent of the given color in normalized float form.
    """
    if _is_hex_str(color):
        color = hex_to_rgb(color)
    elif _is_rgb8_tuple(color):
        color = rgb8_to_rgb(color)
    elif _is_rgba8_tuple(color):
        color = rgba8_to_rgba(color)
    if not (_is_rgb_tuple(color, min_value=0.0, max_value=1.0) or _is_rgba_tuple(color, min_value=0.0, max_value=1.0)):
        raise TypeError("Expected an RGB or RGBA tuple")
    return tuple(color) if len(color) == 4 else (*color, 1.0)


def rgb_to_rgb8(rgb: RGB) -> RGB8:
    """Convert a normalized float RGB tuple into 8-bit integer channels."""
    if not _is_rgb_tuple(rgb, min_value=0.0, max_value=1.0):
        raise ValueError("RGB values must be three floats from 0.0 to 1.0")
    return tuple(_to_8bit_int(channel) for channel in rgb)


def rgba_to_rgba8(rgba: RGBA) -> RGBA8:
    """Convert a normalized float RGBA tuple into 8-bit integer channels."""
    if not _is_rgba_tuple(rgba, min_value=0.0, max_value=1.0):
        raise ValueError("RGBA values must be four floats from 0.0 to 1.0")
    return tuple(_to_8bit_int(channel) for channel in rgba)


def rgb8_to_rgb(rgb8: RGB8) -> RGB:
    """Convert an 8-bit integer RGB tuple into a normalized float tuple."""
    if not _is_rgb8_tuple(rgb8):
        raise ValueError("RGB8 values must be three integers from 0 to 255")
    return tuple(_to_normalized_float(channel) for channel in rgb8)


def rgba8_to_rgba(rgba8: RGBA8) -> RGBA:
    """Convert an 8-bit integer RGBA tuple into a normalized float tuple."""
    if not _is_rgba8_tuple(rgba8):
        raise ValueError("RGBA8 values must be four integers from 0 to 255")
    return tuple(_to_normalized_float(channel) for channel in rgba8)


def srgb_to_linear_rgba(color: RGB | RGBA) -> RGBA:
    """Convert an sRGB color to linear color space, preserving alpha.

    Args:
        color: An (r, g, b) or (r, g, b, a) tuple of floats in [0, 1].

    Returns:
        The (r, g, b, a) equivalent of the given color in linear color space.
    """
    if not (_is_rgb_tuple(color, min_value=0.0, max_value=1.0) or _is_rgba_tuple(color, min_value=0.0, max_value=1.0)):
        raise TypeError("Expected an RGB or RGBA tuple")
    rgba = to_rgba(color)
    linear = Color(rgba[:3]).from_srgb_to_scene_linear()
    return (*linear, rgba[3])


def hex_to_rgb(hex_color: HEX) -> RGB:
    """Convert a HEX color string to a normalized float RGB tuple.

    Args:
        hex_color: A HEX color string, e.g., "#FF00AA" or "FF00AA".

    Returns:
        The corresponding RGB tuple with normalized float values.
    """
    if not _is_hex_str(hex_color):
        if not isinstance(hex_color, str):
            raise TypeError("Expected a HEX color string")
        raise ValueError("Expected a 6-digit HEX color")
    hex_color = hex_color.strip().lstrip("#")
    rgb8 = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return rgb8_to_rgb(rgb8)


def hex_to_rgb8(hex_color: HEX) -> RGB8:
    """Convert a HEX color string to an 8-bit integer RGB tuple.
    Args:
        hex_color: A HEX color string, e.g., "#FF00AA" or "FF00AA".

    Returns:
        The corresponding 8-bit integer RGB tuple.
    """
    return rgb_to_rgb8(hex_to_rgb(hex_color))


def rgb_to_hex(rgb: RGB) -> HEX:
    """Convert a normalized float RGB tuple to a HEX color string."""
    if not _is_rgb_tuple(rgb, min_value=0.0, max_value=1.0):
        raise ValueError("RGB values must be three floats from 0.0 to 1.0")
    return "#{:02X}{:02X}{:02X}".format(*[int(round(channel * 255)) for channel in rgb])


def rgb8_to_hex(rgb8: RGB8) -> HEX:
    """Convert an 8-bit integer RGB tuple to a HEX color string."""
    if not _is_rgb8_tuple(rgb8):
        raise ValueError("RGB8 values must be three integers from 0 to 255")
    return "#{:02X}{:02X}{:02X}".format(*[int(round(channel)) for channel in rgb8])


# Private helper functions for color validation and conversion --------------------------------------------- #


def _is_numeric_channel(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_color_tuple(value: object, size: int, *, min_value: float | int, max_value: float | int) -> bool:
    return (
        isinstance(value, tuple)
        and len(value) == size
        and all(_is_numeric_channel(channel) for channel in value)
        and all(min_value <= channel <= max_value for channel in value)
    )


def _is_rgb_tuple(value: object, *, min_value: float | int = 0.0, max_value: float | int = 1.0) -> bool:
    return _is_color_tuple(value, 3, min_value=min_value, max_value=max_value)


def _is_rgba_tuple(value: object, *, min_value: float | int = 0.0, max_value: float | int = 1.0) -> bool:
    return _is_color_tuple(value, 4, min_value=min_value, max_value=max_value)


def _is_rgb8_tuple(value: object) -> bool:
    return _is_color_tuple(value, 3, min_value=0, max_value=255) and all(
        isinstance(channel, int) and not isinstance(channel, bool) for channel in value
    )


def _is_rgba8_tuple(value: object) -> bool:
    return _is_color_tuple(value, 4, min_value=0, max_value=255) and all(
        isinstance(channel, int) and not isinstance(channel, bool) for channel in value
    )


def _is_hex_str(value: object) -> bool:
    if not isinstance(value, str):
        return False
    candidate = value.strip().lstrip("#")
    return len(candidate) == 6 and all(ch in "0123456789abcdefABCDEF" for ch in candidate)


def _to_normalized_float(value: float | int) -> float:
    if not _is_numeric_channel(value):
        raise TypeError("Expected a numeric color channel")
    if value < 0 or value > 255:
        raise ValueError("Color channel values must be between 0 and 255 for 8-bit conversion")
    return float(value) / 255.0


def _to_8bit_int(value: float | int) -> int:
    if not _is_numeric_channel(value):
        raise TypeError("Expected a numeric color channel")
    if value < 0.0 or value > 1.0:
        raise ValueError("Normalized color channel values must be between 0 and 1")
    return int(round(value * 255))
