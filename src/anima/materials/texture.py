"""PBR texture maps for materials, projected from shared world-space XY coordinates.

Every texture is sampled at the world XY position of the shaded point (divided by the texture's physical
size), so any object lying over a textured surface sees exactly the pixels beneath it, regardless of its own
UVs, and keeps doing so while it moves or animates. This assumes the textured surface lies in the XY plane.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Literal

import bpy

from anima.materials.material import RGBA, to_rgba

AlbedoMode = Literal["replace", "multiply", "ignore"]

NODE_PREFIX = "anima_texture_"
NATIVE_COLOR_NODE = NODE_PREFIX + "native_color"

# Filename suffixes (case-insensitive, without extension) recognised by TextureSet.from_directory().
_SUFFIXES = {
    "albedo": ("albedo", "diffuse", "basecolor", "base_color", "color"),
    "roughness": ("roughness",),
    "normal": ("normal",),
    "height": ("displacement", "height", "bump"),
    "ao": ("ao", "ambientocclusion"),
    "transmission": ("transmission", "translucency"),
    "metallic": ("metallic", "metalness"),
}
_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".exr")


@dataclass
class TextureSet:
    """A collection of PBR texture map files and their physical size.

    Attributes:
        albedo: Diffuse/base color map (sRGB).
        roughness: Roughness map.
        normal: Tangent-space normal map (OpenGL convention).
        height: Height/displacement map.
        ao: Ambient occlusion map.
        transmission: Transmission map.
        metallic: Metallic map.
        physical_size: Scene-unit extent covered by one tile of the textures (width, height).
    """

    albedo: Path | None = None
    roughness: Path | None = None
    normal: Path | None = None
    height: Path | None = None
    ao: Path | None = None
    transmission: Path | None = None
    metallic: Path | None = None
    physical_size: tuple[float, float] = (1.0, 1.0)

    @classmethod
    def from_directory(
        cls,
        directory: str | Path,
        *,
        physical_size: float | tuple[float, float] = 1.0,
        prefer_exr_height: bool = False,
    ) -> TextureSet:
        """Detect texture maps in a directory from their filename suffixes (e.g. `*_Albedo.jpg`).

        Args:
            directory: The folder containing the maps.
            physical_size: Scene-unit size of one texture tile; a single number means a square tile.
            prefer_exr_height: Prefer a float `.exr` height map over an 8-bit one when both exist.

        Raises:
            FileNotFoundError: If the directory doesn't exist.

        Returns:
            The detected texture set. Maps that aren't found are left as None.
        """
        directory = Path(directory).expanduser()
        if not directory.is_dir():
            raise FileNotFoundError(f"Texture directory not found: {directory}")
        size = (physical_size, physical_size) if isinstance(physical_size, int | float) else tuple(physical_size)

        found: dict[str, Path] = {}
        for path in sorted(directory.iterdir()):
            if path.suffix.lower() not in _IMAGE_EXTENSIONS:
                continue
            stem = path.stem.lower()
            for key, suffixes in _SUFFIXES.items():
                if not any(stem.endswith("_" + s) or stem == s for s in suffixes):
                    continue
                is_exr = path.suffix.lower() == ".exr"
                if key not in found or (key == "height" and is_exr == prefer_exr_height):
                    found[key] = path
                break
        return cls(**found, physical_size=size)

    def maps(self) -> dict[str, Path]:
        """Return the maps that are set, keyed by field name."""
        return {
            f.name: getattr(self, f.name) for f in fields(self) if f.name != "physical_size" and getattr(self, f.name)
        }


def apply_texture_set(
    mat: bpy.types.Material,
    textures: TextureSet,
    *,
    albedo_mode: AlbedoMode = "replace",
    albedo_strength: float = 1.0,
    use_ao: bool = True,
    use_transmission: bool = False,
    bump_strength: float = 0.2,
    bump_distance: float = 0.01,
    normal_strength: float = 1.0,
) -> None:
    """Build the texture node graph on a material's Principled BSDF, replacing any earlier one.

    Args:
        mat: The material to texture.
        textures: The texture maps to apply.
        albedo_mode: "replace" drives Base Color from the albedo map. "multiply" multiplies the material's own
            color by the luminance of the albedo map, preserving its hue. "ignore" leaves Base Color alone.
            The AO map, if used, is multiplied in for "replace" and "multiply".
        albedo_strength: Blend factor (0-1) of the albedo luminance for "multiply".
        use_ao: Multiply the AO map into the base color.
        use_transmission: Drive Transmission Weight from the transmission map.
        bump_strength: Strength of the height-map bump.
        bump_distance: Distance (scene units) a full-intensity height value represents for bump shading.
        normal_strength: Strength of the normal map.
    """
    remove_texture_nodes(mat)
    tree = mat.node_tree
    if tree is None:
        return
    bsdf = tree.nodes.get("Principled BSDF")
    if bsdf is None:
        return
    nodes, links = tree.nodes, tree.links

    def new(kind: str, name: str, x: float, y: float) -> bpy.types.Node:
        node = nodes.new(kind)
        node.name = node.label = NODE_PREFIX + name
        node.location = (bsdf.location.x - x, bsdf.location.y + y)
        return node

    position = new("ShaderNodeNewGeometry", "position", 1400, 0)
    mapping = new("ShaderNodeMapping", "mapping", 1200, 0)
    sx, sy = textures.physical_size
    mapping.inputs["Scale"].default_value = (1.0 / sx, 1.0 / sy, 1.0)
    links.new(position.outputs["Position"], mapping.inputs["Vector"])

    def image(key: str, colorspace: str, x: float, y: float) -> bpy.types.Node | None:
        path = getattr(textures, key)
        if path is None:
            return None
        node = new("ShaderNodeTexImage", key, x, y)
        node.image = _load_image(path, colorspace)
        links.new(mapping.outputs["Vector"], node.inputs["Vector"])
        return node

    color_out = None  # The color socket to feed Base Color, if any.
    albedo = image("albedo", "sRGB", 900, 600) if albedo_mode != "ignore" else None
    if albedo is not None:
        color_out = albedo.outputs["Color"]
        if albedo_mode == "multiply":
            native = new("ShaderNodeRGB", "native_color", 900, 900)
            native.outputs[0].default_value = tuple(mat.diffuse_color)
            luminance = new("ShaderNodeRGBToBW", "luminance", 650, 600)
            links.new(albedo.outputs["Color"], luminance.inputs["Color"])
            tint = new("ShaderNodeMix", "tint", 400, 750)
            tint.data_type = "RGBA"
            tint.blend_type = "MULTIPLY"
            tint.inputs["Factor"].default_value = albedo_strength
            links.new(native.outputs[0], tint.inputs["A"])
            links.new(luminance.outputs["Val"], tint.inputs["B"])
            color_out = tint.outputs["Result"]

    ao = image("ao", "Non-Color", 900, 300) if use_ao and albedo_mode != "ignore" else None
    if ao is not None:
        if color_out is None:  # "ignore" never reaches here, so the base color is the native one.
            native = new("ShaderNodeRGB", "native_color", 900, 900)
            native.outputs[0].default_value = tuple(mat.diffuse_color)
            color_out = native.outputs[0]
        ao_mul = new("ShaderNodeMix", "ao_multiply", 200, 500)
        ao_mul.data_type = "RGBA"
        ao_mul.blend_type = "MULTIPLY"
        ao_mul.inputs["Factor"].default_value = 1.0
        links.new(color_out, ao_mul.inputs["A"])
        links.new(ao.outputs["Color"], ao_mul.inputs["B"])
        color_out = ao_mul.outputs["Result"]
    if color_out is not None:
        links.new(color_out, bsdf.inputs["Base Color"])

    for key, socket in (("roughness", "Roughness"), ("metallic", "Metallic")):
        node = image(key, "Non-Color", 900, 0 if key == "roughness" else -300)
        if node is not None:
            links.new(node.outputs["Color"], bsdf.inputs[socket])

    if use_transmission:
        node = image("transmission", "Non-Color", 900, -600)
        if node is not None:
            links.new(node.outputs["Color"], bsdf.inputs["Transmission Weight"])

    normal_socket = None
    normal_tex = image("normal", "Non-Color", 900, -900)
    if normal_tex is not None:
        normal_map = new("ShaderNodeNormalMap", "normal_map", 400, -900)
        # Surfaces lie in the XY plane and have no reliable UVs, so tangent space equals world space.
        normal_map.space = "WORLD"
        normal_map.inputs["Strength"].default_value = normal_strength
        links.new(normal_tex.outputs["Color"], normal_map.inputs["Color"])
        normal_socket = normal_map.outputs["Normal"]

    height = image("height", "Non-Color", 900, -1200)
    if height is not None:
        bump = new("ShaderNodeBump", "bump", 400, -1200)
        bump.inputs["Strength"].default_value = bump_strength
        bump.inputs["Distance"].default_value = bump_distance
        links.new(height.outputs["Color"], bump.inputs["Height"])
        if normal_socket is not None:
            links.new(normal_socket, bump.inputs["Normal"])
        normal_socket = bump.outputs["Normal"]
    if normal_socket is not None:
        links.new(normal_socket, bsdf.inputs["Normal"])


def remove_texture_nodes(mat: bpy.types.Material) -> None:
    """Remove every node created by apply_texture_set() and restore the plain Principled BSDF links.

    Args:
        mat: The material from which to remove texture nodes.
    """
    if mat.node_tree is None:
        return
    nodes = mat.node_tree.nodes
    native = nodes.get(NATIVE_COLOR_NODE)
    if native is not None:
        bsdf = nodes.get("Principled BSDF")
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = tuple(native.outputs[0].default_value)
    for node in [n for n in nodes if n.name.startswith(NODE_PREFIX)]:
        nodes.remove(node)


def set_native_color(mat: bpy.types.Material, color: RGBA) -> None:
    """Update the color preserved under texture multiplication, if the material has one.

    Args:
        mat: The material to update.
        color: The RGBA color to set as the native color.
    """
    if mat.node_tree is None:
        return
    native = mat.node_tree.nodes.get(NATIVE_COLOR_NODE)
    if native is not None:
        native.outputs[0].default_value = to_rgba(color)


def _load_image(path: Path, colorspace: str) -> bpy.types.Image:
    """Load an image from the given path and set its colorspace.

    Args:
        path: The file path to the image.
        colorspace: The colorspace to assign to the loaded image.

    Returns:
        The loaded Blender image.

    Raises:
        FileNotFoundError: If the image file does not exist.
    """
    path = Path(path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Texture map not found: {path}")
    img = bpy.data.images.load(str(path), check_existing=True)
    img.colorspace_settings.name = colorspace
    return img
