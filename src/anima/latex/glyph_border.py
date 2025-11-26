import svgpathtools as svgtools

from anima.primitives.bezier_curve import BezierCurve
from anima.primitives.curves import Curve
from anima.primitives.lines import Segment


class Subpath:
    """A continuous, closed portion of a glyph's path consisting of multiple curves."""

    def __init__(self, path: type[svgtools.Path]):
        """Initialize a Subpath from an SVG path.

        Args:
            path: A closed svgtools.Path object representing the subpath
        """
        assert path.isclosed(), "A subpath must be a closed path"
        self.path: type[svgtools.Path] = path
        self.curves: list[type[Curve]] = []

        self._create_curves()

    def _create_curves(self):
        """Create a Curve object for each segment of this subpath's path.

        The curves are reflected about the x-axis and then reversed in order to maintain
        the correct winding order (CCW for outer boundaries, CW for holes) required by
        the triangulation algorithm.
        """
        for seg in self.path:
            start = seg.start
            end = seg.end
            p0 = (start.real, start.imag)
            p1 = (end.real, end.imag)

            if isinstance(seg, svgtools.Line):
                curve = Segment(p0, p1)
            elif isinstance(seg, svgtools.CubicBezier):
                ctrl1 = seg.control1
                ctrl2 = seg.control2
                c0 = (ctrl1.real, ctrl1.imag)
                c1 = (ctrl2.real, ctrl2.imag)
                curve = BezierCurve(p0, p1, control_pts=[c0, c1])
            else:
                raise ValueError(f"Unsupported segment type: {type(seg)}")

            # Reflect about x-axis to match Blender's coordinate system
            curve.reflect((0, 1))
            self.curves.append(curve)

        # Reverse curve order to compensate for reflection's winding order reversal
        self.curves.reverse()


class GlyphBorder:
    """A GlyphBorder represents the border of a glyph, comprising one or more subpaths.

    The orientation (CCW/CW) of the subpaths determines whether they are outer boundaries
    or holes. There must be exactly one outer boundary (CCW) and zero or more holes (CW).

    Attributes:
        subpaths: List of Subpath objects representing the glyph border components
    """

    def __init__(self, path: svgtools.Path):
        """Initialize a GlyphBorder from an SVG path.

        Args:
            path: An svgtools.Path object representing the glyph border
        """
        assert isinstance(path, svgtools.Path), "Path must be an instance of svgtools.Path"
        self.subpaths: list[Subpath] = [Subpath(s) for s in path.continuous_subpaths()]
