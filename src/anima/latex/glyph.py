from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import svgpathtools as svgtools

from anima.latex.glyph_body import GlyphBody, MeshQuality
from anima.latex.glyph_border import GlyphBorder
from anima.primitives.object import Object

if TYPE_CHECKING:
    from anima.animation.effects import Effect


@dataclass
class GlyphBBox:
    """Bounding box for a glyph in its local outline coordinates."""

    x_min: float = 0
    x_max: float = 0
    y_min: float = 0
    y_max: float = 0


class Glyph(Object):
    """A Glyph is a single character rendered from LaTeX/SVG.

    It always creates a GlyphBody (the filled mesh) and optionally creates a GlyphBorder
    (the outline curves) as animable children. This enables hierarchical animation and
    transformation of the entire glyph as a single unit.

    Attributes:
        text: The character this glyph represents.
        bbox: The bounding box of the glyph.
        border: The optional GlyphBorder containing the outline curves; None when omitted.
        body: The GlyphBody containing the filled mesh.
    """

    # The progress windows in which the outline is drawn and the fill fades in. They overlap, so the
    # fill starts to appear before the outline is complete.
    BORDER_REVEAL_WINDOW = (0.0, 0.7)
    BODY_REVEAL_WINDOW = (0.5, 1.0)

    def __init__(
        self,
        outline: svgtools.Path,
        name: str = None,
        mesh_quality: MeshQuality | None = None,
        *,
        with_border: bool = False,
    ):
        """Initialize a Glyph from an SVG outline.

        Args:
            outline: The SVG outline representing the glyph.
            name: Optional name for this glyph (defaults to "Glyph").
            mesh_quality: Triangulation density/quality for the glyph body.
                Defaults to MeshQuality.minimal().
            with_border: Whether to create an animatable outline. Defaults to False.
        """
        assert isinstance(outline, svgtools.Path), "Outline must be an instance of svgpathtools.Path"

        name = name or "Glyph"
        super().__init__(name=name)

        # Invert bbox y-coordinates to match Blender's coordinate system
        bbox = GlyphBBox(*outline.bbox())
        bbox.y_min *= -1
        bbox.y_max *= -1

        self.text: str = ""
        self.bbox: GlyphBBox = bbox

        self._border: GlyphBorder | None = None
        if with_border:
            self._border = GlyphBorder(outline, name=f"{name}_border")
            self.add_child(self._border)

        self._body = GlyphBody(name=f"{name}_body", mesh_quality=mesh_quality, outline=outline)
        self.add_child(self._body)

    @property
    def border(self) -> GlyphBorder | None:
        """Get the glyph's optional border (outline curves).

        Returns:
            The GlyphBorder, or None when the glyph was created without an outline.
        """
        return self._border

    @property
    def body(self) -> GlyphBody:
        """Get the glyph's body (filled mesh).

        Returns:
            The GlyphBody containing the filled mesh.
        """
        return self._body


def glyph_write_on(glyph: Glyph) -> Effect:
    """Create an explicit effect that draws a glyph's outline and fades in its fill.

    All the loops of the outline, including holes, are drawn together. This is a reusable recipe, not an implicit
    default assigned to every glyph.

    Args:
        glyph: The glyph to animate.

    Returns:
        A phase effect for drawing the outline and fading in the body.

    Raises:
        ValueError: If the glyph was created without a border.
    """
    from anima.animation.effects import Draw, Fade, Phase, Stagger

    border = glyph.border
    if border is None:
        raise ValueError("Glyph write-on requires with_border=True.")

    return Phase(
        glyph,
        [
            (Stagger(border, lag_ratio=0.0, child_effect=Draw), *glyph.BORDER_REVEAL_WINDOW),
            (Fade(glyph.body), *glyph.BODY_REVEAL_WINDOW),
        ],
    )
