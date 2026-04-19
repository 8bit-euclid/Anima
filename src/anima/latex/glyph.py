from dataclasses import dataclass

import svgpathtools as svgtools

from anima.latex.glyph_body import GlyphBody
from anima.latex.glyph_border import GlyphBorder
from anima.primitives.object import Object


@dataclass
class GlyphBBox:
    """Bounding box for a glyph. Units are in SVG points."""

    x_min: float = 0
    x_max: float = 0
    y_min: float = 0
    y_max: float = 0


class Glyph(Object):
    """A Glyph is a single character rendered from LaTeX/SVG.

    It composes a GlyphBorder (the outline curves) and a GlyphBody (the filled mesh)
    as animable children. This enables hierarchical animation and transformation of
    the entire glyph as a single unit.

    Attributes:
        text: The character this glyph represents.
        bbox: The bounding box of the glyph.
        border: The GlyphBorder containing the outline curves.
        body: The GlyphBody containing the filled mesh.
    """

    def __init__(self, path: svgtools.Path, name: str = None):
        """Initialize a Glyph from an SVG path.

        Args:
            path: The SVG path object representing the glyph.
            name: Optional name for this glyph (defaults to "Glyph").
        """
        assert isinstance(path, svgtools.Path), "Path must be an instance of svgpathtools.Path"

        name = name or "Glyph"
        super().__init__(name=name)

        # Invert bbox y-coordinates to match Blender's coordinate system
        bbox = GlyphBBox(*path.bbox())
        bbox.y_min *= -1
        bbox.y_max *= -1

        self.text: str = ""
        self.bbox: GlyphBBox = bbox

        # Create border and add as child
        self._border = GlyphBorder(path, name=f"{name}_border")
        self.add_subobject(self._border)

        # Create body and add as child
        self._body = GlyphBody(self._border, name=f"{name}_body")
        self.add_subobject(self._body)

    @property
    def border(self) -> GlyphBorder:
        """Get the glyph's border (outline curves).

        Returns:
            The GlyphBorder containing the outline curves.
        """
        return self._border

    @property
    def body(self) -> GlyphBody:
        """Get the glyph's body (filled mesh).

        Returns:
            The GlyphBody containing the filled mesh.
        """
        return self._body
