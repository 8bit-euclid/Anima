import svgpathtools as svgtools
from dataclasses import dataclass
from anima.globals.general import Vector
from anima.primitives.curves import Curve
from anima.primitives.bezier_curve import BezierCurve
from anima.primitives.lines import Segment
from anima.primitives.mesh import Mesh


@dataclass
class GlyphBBox:
    x_min: float = 0
    x_max: float = 0
    y_min: float = 0
    y_max: float = 0


class Subpath:
    """A subpath is a continuous and closed path of a glyph, which can consist of multiple curves."""

    def __init__(self, path: type[svgtools.Path]):
        """Initialize a subpath with a given svgtools Path object.
        Args:
            path: A svgtools.Path object representing the subpath.
        Raises:
            ValueError: If the path is not closed.
        """
        assert path.isclosed(), " A subpath must be a closed path."
        self.path: type[svgtools.Path] = path
        self.curves: list[type[Curve]] = []
        self.vertices: list[type[Vector]] = []

        self._construct()

    def _construct(self):
        """Construct the subpath by creating curves and vertices."""
        self._create_curves()
        self._create_vertices()

    def _create_curves(self):
        """Create a Curve object for each segment of this subpath's path."""
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

            # Store base curve for the current segment (located with respect to origin).
            curve.reflect((0, 1))
            # curve.hide()  # Must unhide when creating instances.
            self.curves.append(curve)

    def _create_vertices(self):
        pass


class GlyphBorder:
    """A GlyphBorder represents the outer border of a glyph, possibly conmprising multiple subpaths. The orientation (cw/ccw) of the subpaths determines whether they are outer or inner loops. There must be exactly one outer loop (ccw) and zero or more inner loops (cw)."""

    def __init__(self, path: svgtools.Path):
        """Initialize a GlyphBorder with a given SVG path object.
        Args:
            path: An svgtools.Path object representing the border of the glyph.
        Raises:
            AssertionError: If the path is not an instance of svgtools.Path.
        """
        assert isinstance(path, svgtools.Path), \
            "Path must be an instance of svgtools.Path"
        self.subpaths: list[Subpath] = \
            [Subpath(s) for s in path.continuous_subpaths()]


class GlyphBody(Mesh):
    def __init__(self, border: GlyphBorder):
        """Initialize a GlyphBody with a given GlyphBorder object.
        Args:
            border: A GlyphBorder object representing the border of the glyph.
        """
        self.border: GlyphBorder = border
        super().__init__()

        self._construct()

    def _construct(self):
        pass


def signed_area(points: list[tuple[float, float]]) -> float:
    """Calculate the signed area of a polygon defined by a list of points.
    Args:
        points: A list of(x, y) tuples representing the vertices of the polygon.
    Returns:
        The signed area of the polygon. Positive if the points are ordered counter-clockwise, negative if clockwise.
    """
    # points: list of (x, y) tuples
    return 0.5 * sum((x1 * y2 - x2 * y1)
                     for (x1, y1), (x2, y2) in zip(points, points[1:] + [points[0]]))


def is_inner_loop(points: list[tuple[float, float]]) -> bool:
    """Determine if the given points form an inner loop(clockwise order).
    Args:
        points: A list of(x, y) tuples representing the vertices of the polygon.
    Returns:
        True if the points are ordered clockwise(inner loop), else False (outer loop).
    """
    return signed_area(points) < 0  # negative = clockwise
