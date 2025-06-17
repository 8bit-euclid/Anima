from anima.latex.glyph_utils import GlyphBody, GlyphBorder, Subpath


class Glyph:
    """A glyph is a unique collection of subpaths, each representing a part of the glyph's shape."""

    def __init__(self, subpaths: list[Subpath] = None):
        self.border: GlyphBorder = GlyphBorder(subpaths) if subpaths else None
        self.body: GlyphBody = GlyphBody(self.border) if self.border else None

    def construct(self):
        """Construct the glyph by creating its subpath curves and mesh."""
        if self.border:
            self.border.construct()
        if self.body:
            self.body.construct()
