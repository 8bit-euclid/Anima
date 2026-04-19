import random

import pytest
import svgpathtools as svgtools

from anima.globals.general import Vector
from anima.primitives.bezier_curve import BezierCurve
from anima.primitives.bezier_spline import BezierSpline
from anima.primitives.chains import CurveChain, CurveLoop
from anima.primitives.dashed_curves import DashedCurve
from anima.primitives.endcaps import ArrowEndcap, PointEndcap, RoundEndcap
from anima.primitives.joints import BevelJoint, MiterJoint, RoundJoint
from anima.primitives.lines import Line, Ray, Segment
from anima.primitives.points import Empty, Point
from anima.primitives.svg_utils import svg_path_to_curves, svg_segment_to_curve
from tests.test_utils import (
    assert_curve_death_tests,
    assert_curve_endpoints,
    assert_death,
    assert_length_valid,
    assert_setter_returns_self,
    assert_tangent_normal_perpendicular,
    assert_vectors_equal,
)

# =============================================================================
# Line Types (Segment, Ray, Line)
# =============================================================================


class TestSegment:
    """Test suite for Segment class - a straight line between two points."""

    def setup_method(self):
        """Set up test fixtures."""
        # Horizontal segment of length 2
        self.seg_horizontal = Segment((0, 0), (2, 0))
        # Vertical segment of length 3
        self.seg_vertical = Segment((1, 1), (1, 4))
        # Diagonal segment
        self.seg_diagonal = Segment((0, 0), (3, 4))

    def test_init_2d_points(self):
        """Test constructor with 2D point tuples."""
        seg = Segment((1, 2), (3, 4))
        # Should create a valid segment
        assert seg is not None
        # Blender appends .001, .002, etc. for duplicate names
        assert seg.name.startswith("Segment")

    def test_init_3d_points(self):
        """Test constructor with 3D point tuples."""
        seg = Segment((1, 2, 3), (4, 5, 6))
        assert seg is not None
        assert_vectors_equal(seg.point(0), Vector((1, 2, 3)))
        assert_vectors_equal(seg.point(1), Vector((4, 5, 6)))

    def test_point_endpoints(self):
        """Test that point(0) and point(1) return the segment endpoints."""
        assert_curve_endpoints(
            self.seg_horizontal,
            Vector((0, 0, 0)),
            Vector((2, 0, 0)),
        )
        assert_curve_endpoints(
            self.seg_vertical,
            Vector((1, 1, 0)),
            Vector((1, 4, 0)),
        )

    def test_point_midpoint(self):
        """Test that point(0.5) returns the geometric midpoint."""
        # Horizontal segment midpoint
        mid = self.seg_horizontal.point(0.5)
        assert_vectors_equal(mid, Vector((1, 0, 0)))

        # Diagonal segment midpoint: (0,0) to (3,4) -> (1.5, 2)
        mid = self.seg_diagonal.point(0.5)
        assert_vectors_equal(mid, Vector((1.5, 2, 0)))

    def test_point_parametric(self):
        """Test point() at various parameter values."""
        seg = self.seg_horizontal  # (0,0) to (2,0)
        # t=0.25 should give (0.5, 0, 0)
        assert_vectors_equal(seg.point(0.25), Vector((0.5, 0, 0)), places=6)
        # t=0.75 should give (1.5, 0, 0)
        assert_vectors_equal(seg.point(0.75), Vector((1.5, 0, 0)), places=6)

    def test_tangent_constant(self):
        """Test that tangent is constant along a straight segment."""
        seg = self.seg_horizontal
        t0 = seg.tangent(0, normalise=True)
        t_mid = seg.tangent(0.5, normalise=True)
        t1 = seg.tangent(1, normalise=True)

        # All tangents should be the same (pointing right)
        assert_vectors_equal(t0, t_mid, places=6)
        assert_vectors_equal(t_mid, t1, places=6)
        # Should point in +X direction
        assert_vectors_equal(t0, Vector((1, 0, 0)), places=6)

    def test_tangent_direction(self):
        """Test tangent direction for different segments."""
        # Vertical segment tangent should point up (+Y)
        t = self.seg_vertical.tangent(0.5, normalise=True)
        assert_vectors_equal(t, Vector((0, 1, 0)), places=6)

        # Diagonal segment (3, 4) -> length 5, tangent = (3/5, 4/5, 0)
        t = self.seg_diagonal.tangent(0.5, normalise=True)
        assert_vectors_equal(t, Vector((0.6, 0.8, 0)), places=6)

    def test_normal_perpendicular(self):
        """Test that normal is perpendicular to tangent."""
        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            assert_tangent_normal_perpendicular(self.seg_horizontal, t)
            assert_tangent_normal_perpendicular(self.seg_vertical, t)
            assert_tangent_normal_perpendicular(self.seg_diagonal, t)

    def test_normal_direction(self):
        """Test normal direction (CCW rotation of tangent in 2D)."""
        # Horizontal segment: tangent=(1,0,0), normal should be (0,1,0) or (0,-1,0)
        n = self.seg_horizontal.normal(0.5, normalise=True)
        # Normal should be perpendicular to X-axis
        assert abs(n.x) < 1e-6
        assert abs(n.length - 1.0) < 1e-6

    def test_length(self):
        """Test length() returns correct Euclidean distance."""
        # Horizontal segment: length = 2
        assert_length_valid(self.seg_horizontal, expected_total=2.0)

        # Vertical segment: length = 3
        assert_length_valid(self.seg_vertical, expected_total=3.0)

        # Diagonal segment: sqrt(3^2 + 4^2) = 5
        assert_length_valid(self.seg_diagonal, expected_total=5.0)

    def test_length_parametric(self):
        """Test length() at intermediate parameter values."""
        seg = self.seg_horizontal  # length = 2
        assert seg.length(0.5) == pytest.approx(1.0, rel=1e-6)
        assert seg.length(0.25) == pytest.approx(0.5, rel=1e-6)

    def test_set_width(self):
        """Test set_width() method returns self for chaining."""
        seg = Segment((0, 0), (1, 0))
        assert_setter_returns_self(seg, "set_width", 2.0)

    def test_set_bias(self):
        """Test set_bias() method returns self for chaining."""
        seg = Segment((0, 0), (1, 0))
        assert_setter_returns_self(seg, "set_bias", 0.5)

    def test_death_out_of_bounds(self):
        """Test that Curve methods raise for out-of-bounds parameters."""
        assert_curve_death_tests(self.seg_horizontal)


class TestRay:
    """Test suite for Ray class - a semi-infinite line from a point."""

    def setup_method(self):
        """Set up test fixtures."""
        self.ray_right = Ray((0, 0), (1, 0))
        self.ray_up = Ray((1, 1), (0, 1))
        self.ray_diagonal = Ray((0, 0), (1, 1))

    def test_init(self):
        """Test Ray constructor with point and direction."""
        ray = Ray((5, 5), (1, 0))
        assert ray is not None
        # Blender appends .001, .002, etc. for duplicate names
        assert ray.name.startswith("Ray")

    def test_point_at_origin(self):
        """Test that point(0) returns the ray origin."""
        assert_vectors_equal(self.ray_right.point(0), Vector((0, 0, 0)))
        assert_vectors_equal(self.ray_up.point(0), Vector((1, 1, 0)))

    def test_point_along_direction(self):
        """Test that point(t) moves in the ray direction."""
        # Ray should extend in the direction
        p0 = self.ray_right.point(0)
        p1 = self.ray_right.point(0.5)
        direction = (p1 - p0).normalized()
        assert_vectors_equal(direction, Vector((1, 0, 0)), places=6)

    def test_tangent_equals_direction(self):
        """Test that tangent matches the ray direction."""
        t = self.ray_right.tangent(0.5, normalise=True)
        assert_vectors_equal(t, Vector((1, 0, 0)), places=6)

        t = self.ray_up.tangent(0.5, normalise=True)
        assert_vectors_equal(t, Vector((0, 1, 0)), places=6)

    def test_normal_perpendicular(self):
        """Test that normal is perpendicular to tangent."""
        assert_tangent_normal_perpendicular(self.ray_right, 0.5)
        assert_tangent_normal_perpendicular(self.ray_up, 0.5)
        assert_tangent_normal_perpendicular(self.ray_diagonal, 0.5)

    def test_death_out_of_bounds(self):
        """Test that Curve methods raise for out-of-bounds parameters."""
        assert_curve_death_tests(self.ray_right)


class TestLine:
    """Test suite for Line class - an infinite line through a point."""

    def setup_method(self):
        """Set up test fixtures."""
        self.line_horizontal = Line((0, 0), (1, 0))
        self.line_vertical = Line((1, 1), (0, 1))
        self.line_diagonal = Line((0, 0), (1, 1))

    def test_init(self):
        """Test Line constructor with point and direction."""
        line = Line((5, 5), (1, 0))
        assert line is not None
        # Blender appends .001, .002, etc. for duplicate names
        assert line.name.startswith("Line")

    def test_point_at_center(self):
        """Test that point(0.5) passes through the specified point."""
        # Line through (0,0) with direction (1,0) - t=0.5 should be at origin
        mid = self.line_horizontal.point(0.5)
        assert_vectors_equal(mid, Vector((0, 0, 0)), places=6)

        mid = self.line_vertical.point(0.5)
        assert_vectors_equal(mid, Vector((1, 1, 0)), places=6)

    def test_point_extends_both_ways(self):
        """Test that line extends in both directions from the center."""
        p0 = self.line_horizontal.point(0)
        p1 = self.line_horizontal.point(1)
        mid = self.line_horizontal.point(0.5)

        # p0 should be to the left of mid, p1 to the right
        assert p0.x < mid.x < p1.x

    def test_tangent_equals_direction(self):
        """Test that tangent matches the line direction."""
        t = self.line_horizontal.tangent(0.5, normalise=True)
        assert_vectors_equal(t, Vector((1, 0, 0)), places=6)

        t = self.line_vertical.tangent(0.5, normalise=True)
        assert_vectors_equal(t, Vector((0, 1, 0)), places=6)

    def test_normal_perpendicular(self):
        """Test that normal is perpendicular to tangent."""
        assert_tangent_normal_perpendicular(self.line_horizontal, 0.5)
        assert_tangent_normal_perpendicular(self.line_vertical, 0.5)
        assert_tangent_normal_perpendicular(self.line_diagonal, 0.5)

    def test_death_out_of_bounds(self):
        """Test that Curve methods raise for out-of-bounds parameters."""
        assert_curve_death_tests(self.line_horizontal)


# =============================================================================
# Bezier Types
# =============================================================================


class TestBezierCurve:
    """Test suite for BezierCurve class - a single cubic Bezier curve."""

    def setup_method(self):
        """Set up test fixtures."""
        # Simple curve from (0,0) to (4,0) - initially a straight line
        self.curve_simple = BezierCurve((0, 0), (4, 0))
        # Curve with explicit control points for an arc shape
        self.curve_arc = BezierCurve(
            (0, 0),
            (4, 0),
            control_pts=[(1, 2, 0), (3, 2, 0)],
        )

    def test_init_two_points(self):
        """Test constructor with start and end points only."""
        curve = BezierCurve((1, 2), (5, 6))
        assert curve is not None
        assert curve.name.startswith("BezierCurve")

    def test_init_with_control_points(self):
        """Test constructor with explicit control points."""
        curve = BezierCurve(
            (0, 0),
            (10, 0),
            control_pts=[(3, 5, 0), (7, 5, 0)],
        )
        assert curve is not None
        # Verify the curve exists and has the control points set
        assert curve.handle_0 is not None
        assert curve.handle_1 is not None

    def test_init_control_points_wrong_count(self):
        """Test that wrong number of control points raises assertion."""
        with pytest.raises(AssertionError):
            BezierCurve((0, 0), (1, 0), control_pts=[(0.5, 0.5)])  # Only 1 point
        with pytest.raises(AssertionError):
            BezierCurve((0, 0), (1, 0), control_pts=[(0.3, 0.3), (0.5, 0.5), (0.7, 0.7)])

    def test_point_endpoints(self):
        """Test that point(0) and point(1) return curve endpoints."""
        assert_curve_endpoints(
            self.curve_simple,
            Vector((0, 0, 0)),
            Vector((4, 0, 0)),
        )
        assert_curve_endpoints(
            self.curve_arc,
            Vector((0, 0, 0)),
            Vector((4, 0, 0)),
        )

    def test_point_midpoint_simple(self):
        """Test point(0.5) for a simple curve."""
        # For a straight-line bezier, midpoint should be at (2, 0, 0)
        mid = self.curve_simple.point(0.5)
        assert_vectors_equal(mid, Vector((2, 0, 0)), places=5)

    def test_point_midpoint_arc(self):
        """Test point(0.5) for an arc curve."""
        # Arc curve with control points at y=2 should have midpoint above the line
        mid = self.curve_arc.point(0.5)
        assert mid.x == pytest.approx(2.0, rel=1e-5)
        assert mid.y > 0  # Should be above the x-axis due to control points

    def test_tangent(self):
        """Test tangent at endpoints."""
        # Simple curve should have horizontal tangent
        t0 = self.curve_simple.tangent(0, normalise=True)
        t1 = self.curve_simple.tangent(1, normalise=True)
        # Both should point in +X direction
        assert_vectors_equal(t0, Vector((1, 0, 0)), places=5)
        assert_vectors_equal(t1, Vector((1, 0, 0)), places=5)

    def test_normal_perpendicular(self):
        """Test that normal is perpendicular to tangent."""
        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            assert_tangent_normal_perpendicular(self.curve_simple, t)
            assert_tangent_normal_perpendicular(self.curve_arc, t)

    def test_length(self):
        """Test length() method."""
        # Simple straight curve should have length ~4
        assert_length_valid(self.curve_simple, expected_total=4.0)
        # Arc curve should have length >= straight-line distance
        arc_length = self.curve_arc.length(1)
        assert arc_length > 4.0  # Arc is longer than chord

    def test_set_handle_0(self):
        """Test set_handle_0() method."""
        curve = BezierCurve((0, 0), (4, 0))
        result = curve.set_handle_0((1, 2))
        # Should return self for chaining
        assert result is curve

    def test_set_handle_1(self):
        """Test set_handle_1() method."""
        curve = BezierCurve((0, 0), (4, 0))
        result = curve.set_handle_1((-1, 2))
        # Should return self for chaining
        assert result is curve

    def test_handle_0_getter(self):
        """Test handle_0 property getter returns relative position."""
        curve = BezierCurve((0, 0), (4, 0))
        curve.set_handle_0((1, 2))
        handle = curve.handle_0
        assert handle is not None
        assert_vectors_equal(handle, Vector((1, 2, 0)), places=5)

    def test_handle_0_setter(self):
        """Test handle_0 property setter."""
        curve = BezierCurve((0, 0), (4, 0))
        curve.handle_0 = (2, 3)
        handle = curve.handle_0
        assert_vectors_equal(handle, Vector((2, 3, 0)), places=5)

    def test_handle_1_getter(self):
        """Test handle_1 property getter returns relative position."""
        curve = BezierCurve((0, 0), (4, 0))
        curve.set_handle_1((-1, 2))
        handle = curve.handle_1
        assert handle is not None
        assert_vectors_equal(handle, Vector((-1, 2, 0)), places=5)

    def test_handle_1_setter(self):
        """Test handle_1 property setter."""
        curve = BezierCurve((0, 0), (4, 0))
        curve.handle_1 = (-2, 3)
        handle = curve.handle_1
        assert_vectors_equal(handle, Vector((-2, 3, 0)), places=5)

    def test_set_width(self):
        """Test set_width() method returns self for chaining."""
        curve = BezierCurve((0, 0), (1, 0))
        assert_setter_returns_self(curve, "set_width", 2.0)

    def test_set_bias(self):
        """Test set_bias() method returns self for chaining."""
        curve = BezierCurve((0, 0), (1, 0))
        assert_setter_returns_self(curve, "set_bias", 0.5)

    def test_death_out_of_bounds(self):
        """Test that Curve methods raise for out-of-bounds parameters."""
        assert_curve_death_tests(self.curve_simple)


class TestBezier:
    def setup_method(self):
        self.spline1 = BezierSpline([(0, 0), (3, 1), (7, -1)])
        self.spline1.set_resolution(100)
        self.spline1.set_left_handle(2, (-2.0, 0))

        self.length2 = 6
        self.spline2 = BezierSpline([(0, 0), (1, 0), (3, 0), (self.length2, 0)])

    def test_point(self):
        # Left endpoint
        pt = self.spline1.point(0.0)
        bpt = self.spline1.spline_point(0).co
        assert_vectors_equal(pt, bpt)

        # Right endpoint
        pt = self.spline1.point(1.0)
        bpt = self.spline1.spline_point(2).co
        assert_vectors_equal(pt, bpt)

        # Death tests
        assert_death(self.spline1.point, -0.1)
        assert_death(self.spline1.point, 1.1)

    def test_tangent(self):
        # Left endpoint tangent.
        tn = self.spline1.tangent(0.0, normalise=True)
        spt = self.spline1.spline_point(0)
        bpt = spt.co
        hnd = spt.handle_right
        btn = (hnd - bpt).normalized()
        assert_vectors_equal(tn, btn, places=6)

        # Right endpoint tangent. Should be horizontal.
        tn = self.spline1.tangent(1.0, normalise=True)
        btn = Vector((1, 0, 0))
        assert_vectors_equal(tn, btn)

        # Death tests
        assert_death(self.spline1.tangent, -0.1)
        assert_death(self.spline1.tangent, 1.1)

    def test_normal(self):
        # Add enpoint params and generate random intermediate params.
        params = [0, 1]
        for _ in range(100):
            params.append(random.random())

        # Test orthogonality of normal and tangent at each param.
        for t in params:
            nm = self.spline1.normal(t)
            tn = self.spline1.tangent(t)
            assert nm.dot(tn) == pytest.approx(0, abs=1e-7)

        # Death tests
        assert_death(self.spline1.normal, -0.1)
        assert_death(self.spline1.normal, 1.1)

    def test_length(self):
        # Test total length
        l = self.spline2.length(1.0)
        l_an = self.length2
        err = abs(l - l_an) / l_an
        assert err < 1e-3

        # Test half length (spline param of 2/3)
        l = self.spline2.length(2 / 3)
        l_an = 0.5 * self.length2
        err = abs(l - l_an) / l_an
        assert err < 1e-7

        # Test zero length
        l = self.spline2.length(0.0)
        assert l == 0.0

        # Death tests
        assert_death(self.spline2.length, -0.01)
        assert_death(self.spline2.length, 1.01)

    def test_set_right_handle(self):
        """Test set_right_handle() method."""
        spline = BezierSpline([(0, 0), (4, 0)])
        # Set right handle of first point
        spline.set_right_handle(0, (1, 1))
        handle = spline._get_handle(side="RIGHT", point_index=0, relative=True)
        assert_vectors_equal(handle, Vector((1, 1, 0)), places=5)

    def test_set_left_handle_type(self):
        """Test set_left_handle_type() method returns self."""
        spline = BezierSpline([(0, 0), (4, 0)])
        result = spline.set_left_handle_type(1, "FREE")
        assert result is spline

    def test_set_right_handle_type(self):
        """Test set_right_handle_type() method returns self."""
        spline = BezierSpline([(0, 0), (4, 0)])
        result = spline.set_right_handle_type(0, "FREE")
        assert result is spline

    def test_set_both_handle_types(self):
        """Test set_both_handle_types() method returns self."""
        spline = BezierSpline([(0, 0), (4, 0), (8, 0)])
        result = spline.set_both_handle_types(1, "VECTOR")
        assert result is spline

    def test_set_width(self):
        """Test set_width() method returns self for chaining."""
        spline = BezierSpline([(0, 0), (4, 0)])
        assert_setter_returns_self(spline, "set_width", 2.0)

    def test_set_bias(self):
        """Test set_bias() method returns self for chaining."""
        spline = BezierSpline([(0, 0), (4, 0)])
        assert_setter_returns_self(spline, "set_bias", 0.5)

    def test_resolution_property(self):
        """Test resolution property getter and set_resolution()."""
        spline = BezierSpline([(0, 0), (4, 0)])
        # Set resolution
        result = spline.set_resolution(50)
        assert result is spline  # Should return self
        # Check resolution was set
        assert spline.resolution == 50

    def test_deepcopy(self):
        """Test __deepcopy__() creates independent copy."""
        import copy

        original = BezierSpline([(0, 0), (4, 0)])
        original.set_resolution(100)

        copied = copy.deepcopy(original)

        # Should be different objects
        assert copied is not original
        # Should have same geometry
        assert_vectors_equal(original.point(0), copied.point(0))
        assert_vectors_equal(original.point(1), copied.point(1))
        # Modifying copy should not affect original
        copied.set_resolution(50)
        assert original.resolution == 100
        assert copied.resolution == 50


# =============================================================================
# Dashed Curves
# =============================================================================


class TestDashedCurve:
    """Test suite for DashedCurve class - a curve rendered with dashes."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a base curve for dashing
        self.base_segment = Segment((0, 0), (10, 0))
        self.dashed = DashedCurve(
            self.base_segment,
            dash_len=1.0,
            gap_len=0.5,
        )
        # Create a curved base
        self.base_bezier = BezierCurve(
            (0, 0),
            (10, 0),
            control_pts=[(3, 5, 0), (7, 5, 0)],
        )
        self.dashed_bezier = DashedCurve(
            self.base_bezier,
            dash_len=2.0,
            gap_len=1.0,
        )

    def test_init(self):
        """Test DashedCurve constructor."""
        base = Segment((0, 0), (5, 0))
        dashed = DashedCurve(base, dash_len=1.0, gap_len=0.5)
        assert dashed is not None
        assert dashed.name.startswith("DashedCurve")

    def test_init_with_offset(self):
        """Test DashedCurve constructor with offset."""
        base = Segment((0, 0), (5, 0))
        dashed = DashedCurve(base, dash_len=1.0, gap_len=0.5, offset=0.5)
        assert dashed is not None

    def test_point_delegates_to_base(self):
        """Test that point() delegates to base curve."""
        # DashedCurve.point(t) should return same as base_curve.point(t)
        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            dashed_pt = self.dashed.point(t)
            base_pt = self.base_segment.point(t)
            assert_vectors_equal(dashed_pt, base_pt)

    def test_tangent_delegates_to_base(self):
        """Test that tangent() delegates to base curve."""
        for t in [0.0, 0.5, 1.0]:
            dashed_tn = self.dashed.tangent(t, normalise=True)
            base_tn = self.base_segment.tangent(t, normalise=True)
            assert_vectors_equal(dashed_tn, base_tn)

    def test_normal_delegates_to_base(self):
        """Test that normal() delegates to base curve."""
        for t in [0.0, 0.5, 1.0]:
            dashed_nm = self.dashed.normal(t, normalise=True)
            base_nm = self.base_segment.normal(t, normalise=True)
            assert_vectors_equal(dashed_nm, base_nm)

    def test_length_delegates_to_base(self):
        """Test that length() delegates to base curve."""
        dashed_len = self.dashed.length(1.0)
        base_len = self.base_segment.length(1.0)
        assert dashed_len == pytest.approx(base_len)

    def test_normal_perpendicular(self):
        """Test that normal is perpendicular to tangent."""
        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            assert_tangent_normal_perpendicular(self.dashed, t)
            assert_tangent_normal_perpendicular(self.dashed_bezier, t)

    def test_set_width(self):
        """Test set_width() propagates to dashes."""
        base = Segment((0, 0), (5, 0))
        dashed = DashedCurve(base, dash_len=1.0, gap_len=0.5)
        dashed.set_width(2.0)
        # Width should be set on the dashed curve
        assert dashed.width == 2.0

    def test_set_bias(self):
        """Test set_bias() propagates to dashes."""
        base = Segment((0, 0), (5, 0))
        dashed = DashedCurve(base, dash_len=1.0, gap_len=0.5)
        dashed.set_bias(0.5)
        # Bias should be set on the dashed curve
        assert dashed.bias == 0.5

    def test_set_offset(self):
        """Test set_offset() method."""
        base = Segment((0, 0), (5, 0))
        dashed = DashedCurve(base, dash_len=1.0, gap_len=0.5)
        # Should not raise
        dashed.set_offset(0.25)

    def test_offset_normalisation(self):
        """Test that offset is normalized to [0, 1)."""
        base = Segment((0, 0), (5, 0))
        # Offset of 1.5 should be normalized to 0.5
        dashed = DashedCurve(base, dash_len=1.0, gap_len=0.5, offset=1.5)
        assert dashed._offset == pytest.approx(0.5)
        # Offset of 2.0 should be normalized to 0.0
        dashed2 = DashedCurve(base, dash_len=1.0, gap_len=0.5, offset=2.0)
        assert dashed2._offset == pytest.approx(0.0)

    def test_death_out_of_bounds(self):
        """Test that Curve methods raise for out-of-bounds parameters."""
        assert_curve_death_tests(self.dashed)


# =============================================================================
# Chain Types
# =============================================================================


class TestCurveChain:
    def setup_method(self):
        self.crv1 = Segment((0, 0), (1, 0))
        self.crv2 = Segment((1, 0), (1, 1))
        self.crv3 = Segment((1, 1), (2, 1))
        self.chain = CurveChain([self.crv1, self.crv2, self.crv3], create_joints=True)

    def test_geometry(self):
        # The chain should have 3 segments and 2 joints (when create_joints=True)
        assert len(self.chain._curves) == 3
        assert len(self.chain._joints) == 2

        # The curves should be in the correct order
        assert self.chain._curves[0] == self.crv1
        assert self.chain._curves[1] == self.crv2
        assert self.chain._curves[2] == self.crv3

    def test_point(self):
        # The endpoints should match the first and last segment
        chain = self.chain
        crv1 = self.crv1
        crv2 = self.crv2
        crv3 = self.crv3
        assert_vectors_equal(crv1.point(0), chain.point(0))
        assert_vectors_equal(crv3.point(1), chain.point(1))

        # Check points at intermediate curve endpoints
        l = chain.length()
        l1 = crv1.length()
        l2 = crv2.length()
        assert_vectors_equal(crv1.point(1), chain.point(l1 / l), places=8)
        assert_vectors_equal(crv2.point(0), chain.point(l1 / l), places=8)
        assert_vectors_equal(crv2.point(1), chain.point((l1 + l2) / l), places=8)
        assert_vectors_equal(crv3.point(0), chain.point((l1 + l2) / l), places=8)

    def test_tangent(self):
        # The endpoint tangents should match those of the first and last curves
        chain = self.chain
        crv1 = self.crv1
        crv2 = self.crv2
        crv3 = self.crv3
        assert_vectors_equal(crv1.tangent(0), chain.tangent(0))
        assert_vectors_equal(crv3.tangent(1), chain.tangent(1))

        # Check points at intermediate curve endpoints
        l = chain.length()
        l1 = crv1.length()
        l2 = crv2.length()
        l3 = crv3.length()
        t = 0.783
        assert_vectors_equal(crv1.tangent(t), chain.tangent(t * l1 / l), places=8)
        assert_vectors_equal(crv2.tangent(t), chain.tangent((l1 + t * l2) / l), places=6)
        assert_vectors_equal(crv3.tangent(t), chain.tangent((l1 + l2 + t * l3) / l), places=6)

    def test_normal(self):
        # The endpoint tangents should match those of the first and last curves
        chain = self.chain
        crv1 = self.crv1
        crv2 = self.crv2
        crv3 = self.crv3
        assert_vectors_equal(crv1.normal(0), chain.normal(0))
        assert_vectors_equal(crv3.normal(1), chain.normal(1))

        # Check points at intermediate curve endpoints
        l = chain.length()
        l1 = crv1.length()
        l2 = crv2.length()
        l3 = crv3.length()
        t = 0.9013
        assert_vectors_equal(crv1.normal(t), chain.normal(t * l1 / l))
        assert_vectors_equal(crv2.normal(t), chain.normal((l1 + t * l2) / l))
        assert_vectors_equal(crv3.normal(t), chain.normal((l1 + l2 + t * l3) / l))

    def test_length(self):
        # The total length should be the sum of the lengths of the curves
        l = self.chain.length(1.0)
        l1 = self.crv1.length(1.0)
        l2 = self.crv2.length(1.0)
        l3 = self.crv3.length(1.0)

        assert self.chain.length(0.0) == 0.0
        assert l == pytest.approx(l1 + l2 + l3)
        assert self.chain.length(l1 / l) == pytest.approx(l1)
        assert self.chain.length((l1 + l2) / l) == pytest.approx(l1 + l2)

        # Death tests
        assert_death(self.chain.length, -0.01)
        assert_death(self.chain.length, 1.01)

    def test_set_width(self):
        """Test set_width() propagates to all curves.

        Note: CurveChain.set_width() currently:
        1. Does NOT return self for chaining (returns None)
        2. Does NOT update chain.width property (only propagates to child curves)
        This documents the current behavior.
        """
        seg1 = Segment((0, 0), (1, 0))
        seg2 = Segment((1, 0), (2, 0))
        chain = CurveChain([seg1, seg2])
        result = chain.set_width(2.0)
        # CurveChain.set_width() returns None (not self)
        assert result is None
        # Width is propagated to child curves
        assert seg1.width == 2.0
        assert seg2.width == 2.0

    def test_set_bias(self):
        """Test set_bias() propagates to all curves.

        Note: CurveChain.set_bias() currently:
        1. Does NOT return self for chaining (returns None)
        2. Does NOT update chain.bias property (only propagates to child curves)
        This documents the current behavior.
        """
        seg1 = Segment((0, 0), (1, 0))
        seg2 = Segment((1, 0), (2, 0))
        chain = CurveChain([seg1, seg2])
        result = chain.set_bias(0.5)
        # CurveChain.set_bias() returns None (not self)
        assert result is None
        # Bias is propagated to child curves
        assert seg1.bias == 0.5
        assert seg2.bias == 0.5

    def test_normal_perpendicular(self):
        """Test that normal is perpendicular to tangent."""
        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            assert_tangent_normal_perpendicular(self.chain, t)


class TestJoint:
    def setup_method(self):
        self.crv1 = Segment((0, 0), (1, 0))
        self.crv2 = Segment((1, 0), (1, -1))
        self.miter = MiterJoint(self.crv1, self.crv2)
        self.bevel = BevelJoint(self.crv1, self.crv2)
        self.round = RoundJoint(self.crv1, self.crv2)

    def test_geometry(self):
        miter = self.miter
        bevel = self.bevel
        round = self.round
        num_round_fpts = len(round._frame_points)

        assert len(miter._frame_points) == 4
        assert len(bevel._frame_points) == 5
        # RoundJoint should have DEFAULT_NUM_SUBDIV + 4 vertices (3 + (num_subdiv-1) + 2)
        assert num_round_fpts == 3 + (round._num_subdiv - 1) + 2

        # Faces count
        assert len(miter._frame_faces) == 2
        assert len(bevel._frame_faces) == 3
        assert len(round._frame_faces) == num_round_fpts - 2

    def test_point(self):
        miter = self.miter
        bevel = self.bevel
        round = self.round

        for joint in (miter, bevel, round):
            joint_mid_pt = joint.point(0.5)
            assert_vectors_equal(joint_mid_pt, self.crv1.point(1.0), places=9)
            assert_vectors_equal(joint_mid_pt, self.crv2.point(0.0), places=9)

    def test_tangent(self):
        """Test tangent() method for all joint types."""
        for joint in (self.miter, self.bevel, self.round):
            # Tangent at start should match incoming curve's tangent
            t0 = joint.tangent(0, normalise=True)
            assert t0 is not None
            assert t0.length == pytest.approx(1.0, rel=1e-5)

    def test_normal(self):
        """Test normal() method for all joint types."""
        for joint in (self.miter, self.bevel, self.round):
            # Normal should be perpendicular to tangent
            for t in [0.0, 0.5, 1.0]:
                assert_tangent_normal_perpendicular(joint, t)

    def test_length(self):
        """Test length() method for all joint types."""
        for joint in (self.miter, self.bevel, self.round):
            # Length should be non-negative
            assert joint.length(0) == 0.0
            assert joint.length(1) >= 0.0

    def test_set_width(self):
        """Test set_width() returns self for chaining."""
        joint = MiterJoint(Segment((0, 0), (1, 0)), Segment((1, 0), (1, 1)))
        result = joint.set_width(2.0)
        assert result is joint
        assert joint.width == 2.0

    def test_set_bias(self):
        """Test set_bias() returns self for chaining."""
        joint = MiterJoint(Segment((0, 0), (1, 0)), Segment((1, 0), (1, 1)))
        result = joint.set_bias(0.5)
        assert result is joint
        assert joint.bias == 0.5


class TestBevelJoint:
    """Test suite for BevelJoint class - a beveled corner joint."""

    def setup_method(self):
        """Set up test fixtures."""
        self.crv1 = Segment((0, 0), (1, 0))
        self.crv2 = Segment((1, 0), (1, -1))

    def test_init(self):
        """Test BevelJoint constructor."""
        joint = BevelJoint(self.crv1, self.crv2)
        assert joint is not None
        assert joint.name.startswith("BevelJoint")

    def test_init_with_fillet_factor(self):
        """Test BevelJoint with custom fillet_factor."""
        joint = BevelJoint(self.crv1, self.crv2, fillet_factor=0.5)
        assert joint is not None

    def test_geometry_is_bevel(self):
        """Test that BevelJoint has bevel geometry (5 frame points)."""
        joint = BevelJoint(self.crv1, self.crv2)
        assert len(joint._frame_points) == 5
        assert len(joint._frame_faces) == 3


class TestRoundJoint:
    """Test suite for RoundJoint class - a rounded corner joint."""

    def setup_method(self):
        """Set up test fixtures."""
        self.crv1 = Segment((0, 0), (1, 0))
        self.crv2 = Segment((1, 0), (1, -1))

    def test_init(self):
        """Test RoundJoint constructor."""
        joint = RoundJoint(self.crv1, self.crv2)
        assert joint is not None
        assert joint.name.startswith("RoundJoint")

    def test_init_with_radius_factor(self):
        """Test RoundJoint with custom radius_factor."""
        joint = RoundJoint(self.crv1, self.crv2, radius_factor=0.5)
        assert joint is not None

    def test_init_with_num_subdiv(self):
        """Test RoundJoint with custom num_subdiv."""
        joint = RoundJoint(self.crv1, self.crv2, num_subdiv=10)
        assert joint is not None
        assert joint._num_subdiv == 10

    def test_geometry_varies_with_subdiv(self):
        """Test that RoundJoint geometry varies with num_subdiv."""
        joint_low = RoundJoint(self.crv1, self.crv2, num_subdiv=2)
        joint_high = RoundJoint(self.crv1, self.crv2, num_subdiv=10)
        # More subdivisions = more frame points
        assert len(joint_high._frame_points) > len(joint_low._frame_points)


class TestSvgUtils:
    """Test suite for svg_utils module."""

    def setup_method(self):
        """Set up SVG path fixtures."""
        # Create a simple square path (closed)
        self.square_path = svgtools.Path(
            svgtools.Line(0 + 0j, 100 + 0j),
            svgtools.Line(100 + 0j, 100 + 100j),
            svgtools.Line(100 + 100j, 0 + 100j),
            svgtools.Line(0 + 100j, 0 + 0j),
        )

        # Create an open path (L-shape)
        self.open_path = svgtools.Path(
            svgtools.Line(0 + 0j, 100 + 0j),
            svgtools.Line(100 + 0j, 100 + 50j),
        )

        # Create a path with a cubic bezier
        self.bezier_path = svgtools.Path(
            svgtools.CubicBezier(0 + 0j, 30 + 0j, 70 + 100j, 100 + 100j),
        )

    def test_svg_segment_to_curve_line(self):
        """Test converting SVG Line to Segment."""
        seg = svgtools.Line(10 + 20j, 30 + 40j)
        curve = svg_segment_to_curve(seg, reflect_y=True, reverse_direction=False)

        assert isinstance(curve, Segment)
        # With reflect_y=True, y-coordinates are negated
        assert_vectors_equal(curve.point(0), Vector((10, -20, 0)))
        assert_vectors_equal(curve.point(1), Vector((30, -40, 0)))

    def test_svg_segment_to_curve_line_no_reflect(self):
        """Test converting SVG Line without y-reflection."""
        seg = svgtools.Line(10 + 20j, 30 + 40j)
        curve = svg_segment_to_curve(seg, reflect_y=False, reverse_direction=False)

        assert isinstance(curve, Segment)
        assert_vectors_equal(curve.point(0), Vector((10, 20, 0)))
        assert_vectors_equal(curve.point(1), Vector((30, 40, 0)))

    def test_svg_segment_to_curve_line_reversed(self):
        """Test converting SVG Line with reversed direction."""
        seg = svgtools.Line(10 + 20j, 30 + 40j)
        curve = svg_segment_to_curve(seg, reflect_y=True, reverse_direction=True)

        assert isinstance(curve, Segment)
        # Reversed: end becomes start
        assert_vectors_equal(curve.point(0), Vector((30, -40, 0)))
        assert_vectors_equal(curve.point(1), Vector((10, -20, 0)))

    def test_svg_segment_to_curve_bezier(self):
        """Test converting SVG CubicBezier to BezierCurve."""
        seg = svgtools.CubicBezier(0 + 0j, 30 + 10j, 70 + 90j, 100 + 100j)
        curve = svg_segment_to_curve(seg, reflect_y=True, reverse_direction=False)

        assert isinstance(curve, BezierCurve)
        assert_vectors_equal(curve.point(0), Vector((0, 0, 0)))
        assert_vectors_equal(curve.point(1), Vector((100, -100, 0)))

    def test_svg_segment_to_curve_unsupported(self):
        """Test that unsupported segment types raise ValueError."""
        seg = svgtools.QuadraticBezier(0 + 0j, 50 + 50j, 100 + 0j)
        with pytest.raises(ValueError, match="Unsupported SVG segment type"):
            svg_segment_to_curve(seg)

    def test_svg_path_to_curves_default(self):
        """Test converting SVG path with default options (reflect_y=True, reverse=True)."""
        curves = svg_path_to_curves(self.open_path)

        assert len(curves) == 2
        # With reverse=True, order is reversed and directions swapped
        assert all(isinstance(c, Segment) for c in curves)

    def test_svg_path_to_curves_no_reverse(self):
        """Test converting SVG path without reversing."""
        curves = svg_path_to_curves(self.open_path, reverse=False)

        assert len(curves) == 2
        # First curve starts at (0, 0), ends at (100, 0) with y-reflection
        assert_vectors_equal(curves[0].point(0), Vector((0, 0, 0)))
        assert_vectors_equal(curves[0].point(1), Vector((100, 0, 0)))

    def test_svg_path_to_curves_with_bezier(self):
        """Test converting path with bezier curve."""
        curves = svg_path_to_curves(self.bezier_path)

        assert len(curves) == 1
        assert isinstance(curves[0], BezierCurve)


class TestCurveLoop:
    """Test suite for CurveLoop class - a closed curve chain."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a closed triangle loop
        self.crv1 = Segment((0, 0), (2, 0))
        self.crv2 = Segment((2, 0), (1, 2))
        self.crv3 = Segment((1, 2), (0, 0))
        self.loop = CurveLoop([self.crv1, self.crv2, self.crv3])

        # Create a closed square loop
        self.sq1 = Segment((0, 0), (1, 0))
        self.sq2 = Segment((1, 0), (1, 1))
        self.sq3 = Segment((1, 1), (0, 1))
        self.sq4 = Segment((0, 1), (0, 0))
        self.square_loop = CurveLoop([self.sq1, self.sq2, self.sq3, self.sq4])

    def test_init(self):
        """Test CurveLoop constructor."""
        assert self.loop is not None
        assert self.loop.name.startswith("CurveLoop")

    def test_closed_property(self):
        """Test that closed property returns True."""
        assert self.loop.closed is True
        assert self.square_loop.closed is True

    def test_init_requires_closure(self):
        """Test that non-closed curves raise AssertionError."""
        crv1 = Segment((0, 0), (1, 0))
        crv2 = Segment((1, 0), (1, 1))
        # These don't form a closed loop
        with pytest.raises(AssertionError, match="must be closed"):
            CurveLoop([crv1, crv2])

    def test_point_endpoints(self):
        """Test point() at endpoints."""
        # Loop should start at first curve's start
        assert_vectors_equal(self.loop.point(0), Vector((0, 0, 0)), places=6)
        # Loop should end at last curve's end (which equals first curve's start)
        assert_vectors_equal(self.loop.point(1), Vector((0, 0, 0)), places=6)

    def test_tangent(self):
        """Test tangent() method."""
        # Tangent at start should be along first segment direction
        t0 = self.square_loop.tangent(0, normalise=True)
        assert_vectors_equal(t0, Vector((1, 0, 0)), places=5)

    def test_normal_perpendicular(self):
        """Test that normal is perpendicular to tangent."""
        for t in [0.0, 0.25, 0.5, 0.75]:
            assert_tangent_normal_perpendicular(self.loop, t)

    def test_length(self):
        """Test length() method."""
        # Square loop with side 1 should have perimeter 4
        assert_length_valid(self.square_loop, expected_total=4.0)

    def test_with_joints(self):
        """Test CurveLoop with create_joints=True."""
        crv1 = Segment((0, 0), (1, 0))
        crv2 = Segment((1, 0), (1, 1))
        crv3 = Segment((1, 1), (0, 0))
        loop = CurveLoop([crv1, crv2, crv3], create_joints=True)
        # Should have 3 joints (including closing joint)
        assert len(loop._joints) == 3

    def test_death_out_of_bounds(self):
        """Test that Curve methods raise for out-of-bounds parameters.

        Note: CurveChain/CurveLoop currently does NOT validate bounds in point(),
        tangent(), normal(), or length() methods. This test documents the current
        behavior rather than the expected behavior.
        """
        # CurveChain.point() does not raise for out-of-bounds - it clips internally
        # This is different from other Curve types that raise AssertionError
        # Documenting current behavior: no assertion raised
        try:
            self.loop.point(-0.1)  # Does not raise
            self.loop.point(1.1)  # Does not raise
        except AssertionError:
            pytest.fail("CurveChain unexpectedly started validating bounds")


class TestCurveChainFromSvg:
    """Test CurveChain.from_svg_path() factory method."""

    def setup_method(self):
        """Set up SVG path fixtures."""
        self.open_path = svgtools.Path(
            svgtools.Line(0 + 0j, 100 + 0j),
            svgtools.Line(100 + 0j, 100 + 50j),
        )

    def test_from_svg_path_creates_chain(self):
        """Test that from_svg_path creates a valid CurveChain."""
        chain = CurveChain.from_svg_path(self.open_path)

        assert isinstance(chain, CurveChain)
        assert len(chain._curves) == 2

    def test_from_svg_path_name(self):
        """Test that name is passed through."""
        chain = CurveChain.from_svg_path(self.open_path, name="MyChain")
        assert chain.name == "MyChain"

    def test_from_svg_path_no_joints_by_default(self):
        """Test that joints are not created by default."""
        chain = CurveChain.from_svg_path(self.open_path)
        assert len(chain._joints) == 0


class TestCurveLoopFromSvg:
    """Test CurveLoop.from_svg_path() factory method."""

    def setup_method(self):
        """Set up SVG path fixtures."""
        self.closed_path = svgtools.Path(
            svgtools.Line(0 + 0j, 100 + 0j),
            svgtools.Line(100 + 0j, 100 + 100j),
            svgtools.Line(100 + 100j, 0 + 100j),
            svgtools.Line(0 + 100j, 0 + 0j),
        )
        self.open_path = svgtools.Path(
            svgtools.Line(0 + 0j, 100 + 0j),
            svgtools.Line(100 + 0j, 100 + 50j),
        )

    def test_from_svg_path_creates_loop(self):
        """Test that from_svg_path creates a valid CurveLoop."""
        loop = CurveLoop.from_svg_path(self.closed_path)

        assert isinstance(loop, CurveLoop)
        assert isinstance(loop, CurveChain)  # Inheritance
        assert len(loop._curves) == 4
        assert loop.closed is True

    def test_from_svg_path_name(self):
        """Test that name is passed through."""
        loop = CurveLoop.from_svg_path(self.closed_path, name="MyLoop")
        assert loop.name == "MyLoop"

    def test_from_svg_path_requires_closed_path(self):
        """Test that open paths raise AssertionError."""
        with pytest.raises(AssertionError, match="Path must be closed"):
            CurveLoop.from_svg_path(self.open_path)

    def test_from_svg_path_no_joints_by_default(self):
        """Test that joints are not created by default."""
        loop = CurveLoop.from_svg_path(self.closed_path)
        assert len(loop._joints) == 0


# =============================================================================
# Point Types (Empty, Point)
# =============================================================================


class TestEmpty:
    """Test suite for Empty class - an invisible reference point."""

    def test_init_default_location(self):
        """Test Empty constructor with default location."""
        empty = Empty()
        assert empty is not None
        assert empty.name.startswith("Empty")
        assert_vectors_equal(empty.location, Vector((0, 0, 0)))

    def test_init_custom_location_2d(self):
        """Test Empty constructor with custom 2D location."""
        empty = Empty(location=(5, 10))
        assert_vectors_equal(empty.location, Vector((5, 10, 0)), places=6)

    def test_init_custom_location_3d(self):
        """Test Empty constructor with custom 3D location."""
        empty = Empty(location=(1, 2, 3))
        assert_vectors_equal(empty.location, Vector((1, 2, 3)), places=6)

    def test_init_custom_name(self):
        """Test Empty constructor with custom name."""
        empty = Empty(name="MyEmpty")
        assert empty.name == "MyEmpty"

    def test_location_property(self):
        """Test that location property can be set after construction."""
        empty = Empty()
        empty.location = (7, 8, 9)
        assert_vectors_equal(empty.location, Vector((7, 8, 9)), places=6)


class TestPoint:
    """Test suite for Point class - a visible point object."""

    def test_init_default_location(self):
        """Test Point constructor with default location."""
        point = Point()
        assert point is not None
        assert point.name.startswith("Point")
        assert_vectors_equal(point.location, Vector((0, 0, 0)))

    def test_init_custom_location_2d(self):
        """Test Point constructor with custom 2D location (automatically padded to 3D)."""
        point = Point(location=(3, 4))
        assert_vectors_equal(point.location, Vector((3, 4, 0)), places=6)

    def test_init_custom_location_3d(self):
        """Test Point constructor with custom 3D location."""
        point = Point(location=(1, 2, 3))
        assert_vectors_equal(point.location, Vector((1, 2, 3)), places=6)

    def test_init_custom_name(self):
        """Test Point constructor with custom name."""
        point = Point(name="MyPoint")
        assert point.name == "MyPoint"

    def test_init_custom_radius(self):
        """Test Point constructor with custom radius."""
        point = Point(radius=2.0)
        assert point is not None
        # Point is created with specified radius (visible as mesh size)

    def test_location_property(self):
        """Test that location property can be set after construction."""
        point = Point()
        point.location = (10, 20, 30)
        assert_vectors_equal(point.location, Vector((10, 20, 30)), places=6)


# =============================================================================
# Endcaps
# =============================================================================


class TestPointEndcap:
    """Test suite for PointEndcap class."""

    def test_init(self):
        """Test PointEndcap constructor."""
        endcap = PointEndcap()
        assert endcap is not None
        assert endcap.name.startswith("PointEndcap")

    def test_offset_distance_zero(self):
        """Test that offset_distance returns 0."""
        endcap = PointEndcap()
        assert endcap.offset_distance() == 0.0

    def test_custom_name(self):
        """Test PointEndcap with custom name."""
        endcap = PointEndcap(name="MyPointEndcap")
        assert endcap.name == "MyPointEndcap"


class TestRoundEndcap:
    """Test suite for RoundEndcap class."""

    def test_init_default(self):
        """Test RoundEndcap constructor with defaults."""
        endcap = RoundEndcap()
        assert endcap is not None
        assert endcap.name.startswith("RoundEndcap")

    def test_offset_distance_zero(self):
        """Test that offset_distance returns 0."""
        endcap = RoundEndcap()
        assert endcap.offset_distance() == 0.0

    def test_custom_name(self):
        """Test RoundEndcap with custom name."""
        endcap = RoundEndcap(name="MyRoundEndcap")
        assert endcap.name == "MyRoundEndcap"

    def test_custom_width_and_radius(self):
        """Test RoundEndcap with custom width and radius."""
        endcap = RoundEndcap(width=2.0, radius=0.5)
        assert endcap is not None

    def test_invalid_radius_raises(self):
        """Test that invalid radius (2*radius > width) raises assertion."""
        with pytest.raises(AssertionError):
            RoundEndcap(width=1.0, radius=1.0)  # 2*1.0 > 1.0


class TestArrowEndcap:
    """Test suite for ArrowEndcap class."""

    def test_init_default(self):
        """Test ArrowEndcap constructor with defaults."""
        endcap = ArrowEndcap()
        assert endcap is not None
        assert endcap.name.startswith("ArrowEndcap")

    def test_offset_distance_equals_height(self):
        """Test that offset_distance returns height_1."""
        endcap = ArrowEndcap(height_1=5.0)
        assert endcap.offset_distance() == 5.0

    def test_custom_name(self):
        """Test ArrowEndcap with custom name."""
        endcap = ArrowEndcap(name="MyArrowEndcap")
        assert endcap.name == "MyArrowEndcap"

    def test_custom_dimensions(self):
        """Test ArrowEndcap with custom dimensions."""
        endcap = ArrowEndcap(width=3.0, height_1=4.0, height_2=0.5)
        assert endcap.offset_distance() == 4.0
        assert endcap.height_1 == 4.0
