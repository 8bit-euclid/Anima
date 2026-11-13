from collections.abc import Iterator
from typing import Any

import bpy
import svgpathtools as svgtools

from anima.materials.material import get_or_create_material, set_material_properties as apply_material_properties
from anima.materials.texture import AlbedoMode, TextureSet, _texture_application, apply_texture_set
from anima.primitives.chains import CurveLoop
from anima.primitives.curves import THIN_LINE_WIDTH, Curve
from anima.primitives.object import Object


class GlyphBorder(Object):
    """A GlyphBorder represents the border of a glyph, comprising one or more closed subpaths.

    The orientation (CCW/CW) of the subpaths determines whether they are outer boundaries
    or holes. There must be exactly one outer boundary (CCW) and zero or more holes (CW).

    Each subpath is represented as a CurveLoop (closed curve chain) and added as a child
    of this object, enabling hierarchical animation and transformation.

    Attributes:
        subpaths: List of CurveLoop objects representing the glyph border components.
    """

    def __init__(self, outline: svgtools.Path, name: str = "GlyphBorder"):
        """Initialize a GlyphBorder from an SVG outline.

        Args:
            outline: An svgtools.Path object representing the glyph border.
            name: Name for this GlyphBorder object.
        """
        assert isinstance(outline, svgtools.Path), "Outline must be an instance of svgtools.Path"
        super().__init__(name=name)

        self._subpaths: list[CurveLoop] = []

        for i, subpath in enumerate(outline.continuous_subpaths()):
            loop = CurveLoop.from_svg_path(
                subpath,
                create_joints=False,  # Skip costly joints for glyph borders
                name=f"{name}_loop_{i}",
            )
            loop.width = THIN_LINE_WIDTH
            loop.bias = -1  # So that the border does not extend beyond the boundary of the body
            self._subpaths.append(loop)
            self.add_child(loop)

    @property
    def subpaths(self) -> list[CurveLoop]:
        """Get the list of CurveLoop subpaths.

        Returns:
            List of CurveLoop objects representing the closed subpaths.
        """
        return self._subpaths

    @property
    def curves(self) -> list[Curve]:
        """Get a flat list of all curves across all subpaths.

        Returns:
            List of all Curve objects from all subpaths.
        """
        return [curve for loop in self._subpaths for curve in loop.curves]

    def set_material_properties(
        self,
        *,
        color: tuple[float, float, float] | tuple[float, float, float, float] | str | None = None,
        roughness: float | None = None,
        metallic: float | None = None,
        specular_ior_level: float | None = None,
        ior: float | None = None,
        coat_weight: float | None = None,
        coat_roughness: float | None = None,
        sheen_weight: float | None = None,
        emission_strength: float | None = None,
        opacity: float | None = None,
    ) -> Object:
        """Set the shared material properties for this glyph border.

        All objects in the border hierarchy use one material. Styling one curve therefore styles the entire border.

        Args:
            color: RGB or RGBA color, or a hex color string.
            roughness: Surface roughness.
            metallic: Metallic response.
            specular_ior_level: Specular reflection strength.
            ior: Index of refraction.
            coat_weight: Clear coat strength.
            coat_roughness: Clear coat roughness.
            sheen_weight: Sheen strength.
            emission_strength: Emission strength.
            opacity: Surface opacity.

        Raises:
            ValueError: If an RGBA color and a separate opacity are both provided.

        Returns:
            This border.
        """
        if isinstance(color, tuple) and len(color) == 4 and opacity is not None:
            raise ValueError("Pass either an RGBA color or opacity, not both.")
        material = self._ensure_shared_material()
        if material is not None:
            apply_material_properties(
                material,
                color=color,
                roughness=roughness,
                metallic=metallic,
                specular_ior_level=specular_ior_level,
                ior=ior,
                coat_weight=coat_weight,
                coat_roughness=coat_roughness,
                sheen_weight=sheen_weight,
                emission_strength=emission_strength,
                opacity=opacity,
            )
        return self

    def set_textures(
        self,
        textures: TextureSet,
        *,
        albedo_mode: AlbedoMode = "replace",
        **options: Any,
    ) -> Object:
        """Apply textures once to the shared border material.

        Args:
            textures: The texture maps to apply.
            albedo_mode: How the albedo map interacts with the material color.
            **options: Further options for :func:`apply_texture_set`.

        Returns:
            This border.
        """
        with _texture_application():
            for node in self._hierarchy_objects():
                node._texture_set = textures
                node._texture_options = {"albedo_mode": albedo_mode, **options}
            material = self._ensure_shared_material()
            if material is not None:
                apply_texture_set(material, textures, albedo_mode=albedo_mode, **options)
        return self

    def _hierarchy_objects(self) -> Iterator[Object]:
        pending = [self]
        while pending:
            node = pending.pop()
            yield node
            pending.extend(reversed(node.children))

    def _ensure_shared_material(self) -> bpy.types.Material | None:
        data_objects = [node for node in self._hierarchy_objects() if node._has_data()]
        if not data_objects:
            return None

        material = next(
            (node.object.data.materials[0] for node in data_objects if node.object.data.materials),
            None,
        )
        if material is None:
            base_name = f"{self.name}_shared_material"
            name = base_name
            suffix = 1
            while bpy.data.materials.get(name) is not None:
                name = f"{base_name}_{suffix}"
                suffix += 1
            material = get_or_create_material(name)

        for node in data_objects:
            materials = node.object.data.materials
            if materials:
                materials[0] = material
            else:
                materials.append(material)
        return material
