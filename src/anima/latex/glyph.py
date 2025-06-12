from anima.latex.glyph_utils import GlyphBody, GlyphBorder, Subpath, compute_subpath_vertices


class Glyph:
    """A glyph is a unique collection of subpaths, each representing a part of the glyph's shape."""

    def __init__(self, subpaths: list[Subpath] = None):
        self.border: GlyphBorder = GlyphBorder(subpaths) if subpaths else None
        self.body: GlyphBody = GlyphBody(self.border) if self.border else None

    def create_curves(self):
        """Create a Curve object for each segment of this glyph's subpaths."""
        for subpath in self.border.subpaths:
            subpath.create_curves()

    def create_mesh(self):
        """Create and store the mesh for this glyph."""
        # Generate vertices for each subpath.
        for subpath in self.border.subpaths:
            verts = compute_subpath_vertices(subpath)

        # Generate faces.
