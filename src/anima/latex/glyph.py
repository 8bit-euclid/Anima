import svgpathtools as svgtools

from anima.latex.glyph_utils import GlyphBBox, GlyphBody, GlyphBorder


class Glyph:
    """A glyph is a unique collection of subpaths, each representing a part of the glyph's shape."""

    def __init__(self, path: svgtools.Path):
        """
        Initialize a Glyph with a list of subpaths and an optional bounding box.
        Args:
            path (svgtools.Path): The SVG path object representing the glyph.
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
