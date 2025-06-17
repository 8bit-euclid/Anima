import svgpathtools as svgtools
from anima.globals.general import Vector
from anima.primitives.curves import Curve
from anima.primitives.bezier import BezierCurve
from anima.primitives.lines import Segment
from anima.primitives.mesh import Mesh


class Subpath:
    """A subpath is a continuous and closed path of a glyph, which can consist of multiple curves."""

    def __init__(self, path: type[svgtools.Path]):
        """Initialize a subpath with a given svgtools Path object.
        Args:
            path: A svgtools.Path object representing the subpath.
        Raises:
            ValueError: If the path is not closed.
        """
        assert path.isclosed()
        self.path: type[svgtools.Path] = path
        self.curves: list[type[Curve]] = []
        self.vertices: list[type[Vector]] = []

    def create_curves(self):
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

    def create_vertices(self):
        pass
        # for curve in self.curves:
        #     # Always start with the first point of the curve.
        #     p0 = curve.point(0)
        #     self.vertices.append(Vector(p0[0], p0[1]))

        #     if isinstance(curve, Segment):
        #         # For segments, no need for intermediate points.
        #         continue
        #     elif isinstance(curve, BezierCurve):
        #         # For Bezier curves, we need to sample points along the curve.
        #         num_samples = 10
        #         for t in range(num_samples + 1):
        #             t = t / num_samples
        #             pt = curve.point(t)
        #             self.vertices.append(Vector(pt[0], pt[1]))
        #     else:
        #         raise Exception(f"Unsupported curve type: {type(curve)}")

        #     l = curve.length()


class GlyphBorder:
    def __init__(self, subpaths: list[type[Subpath]]):
        """Initialize a GlyphBorder with a given list of subpaths.
        Args:
            subpaths: A list of Subpath objects representing the border of the glyph.
        """
        self.subpaths: list[type[Subpath]] = subpaths

    def construct(self):
        """Construct the border by creating curves and vertices for each subpath."""
        for subpath in self.subpaths:
            subpath.create_curves()
            subpath.create_vertices()


class GlyphBody(Mesh):
    def __init__(self, border: GlyphBorder):
        """Initialize a GlyphBody with a given GlyphBorder object.
        Args:
            border: A GlyphBorder object representing the border of the glyph.
        """
        self.border: GlyphBorder = border
        super().__init__()

    def construct(self):
        pass
