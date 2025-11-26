from dataclasses import dataclass

import svgpathtools as svgtools

from anima.latex.glyph_body import GlyphBody
from anima.latex.glyph_border import GlyphBorder


@dataclass
class GlyphBBox:
    """Bounding box for a glyph. Units are in SVG points."""

    x_min: float = 0
    x_max: float = 0
    y_min: float = 0
    y_max: float = 0


class Glyph:
    """A glyph is a unique collection of subpaths, each representing a part of the glyph's shape."""

    def __init__(self, path: svgtools.Path):
        """Initialize a Glyph with a list of subpaths and an optional bounding box.

        Args:
            path: The SVG path object representing the glyph.
        """
        assert isinstance(path, svgtools.Path), "Path must be an instance of svgpathtools.Path"

        # Invert bbox y-coordinates
        bbox = GlyphBBox(*path.bbox())
        bbox.y_min *= -1
        bbox.y_max *= -1

        self.text: str = ""
        self.bbox: GlyphBBox = bbox
        self.border: GlyphBorder = GlyphBorder(path)
        self.body: GlyphBody = GlyphBody(self.border)
