import svgpathtools as svgtools

from anima.primitives.chains import CurveLoop
from anima.primitives.curves import Curve
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

    def __init__(self, path: svgtools.Path, name: str = "GlyphBorder"):
        """Initialize a GlyphBorder from an SVG path.

        Args:
            path: An svgtools.Path object representing the glyph border.
            name: Name for this GlyphBorder object.
        """
        assert isinstance(path, svgtools.Path), "Path must be an instance of svgtools.Path"
        super().__init__(name=name)

        self._subpaths: list[CurveLoop] = []

        for i, subpath in enumerate(path.continuous_subpaths()):
            loop = CurveLoop.from_svg_path(
                subpath,
                create_joints=False,  # Skip costly joints for glyph borders
                name=f"{name}_loop_{i}",
            )
            self._subpaths.append(loop)
            self.add_subobject(loop)

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
