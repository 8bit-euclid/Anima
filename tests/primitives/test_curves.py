import pytest
import random
from anima.globals.general import Vector
from anima.primitives.lines import Segment
from anima.primitives.bezier_spline import BezierSpline
from anima.primitives.chains import CurveChain
from anima.primitives.joints import MiterJoint, BevelJoint, RoundJoint
from tests.test_utils import assert_death, assert_vectors_equal


class TestBezier:
    def setup_method(self):
        self.spline1 = BezierSpline([(0, 0), (3, 1), (7, -1)])
        self.spline1.set_resolution(100)
        self.spline1.set_left_handle(2, (-2.0, 0))

        self.length2 = 6
        self.spline2 = BezierSpline(
            [(0, 0), (1, 0), (3, 0), (self.length2, 0)])

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
        for i in range(100):
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
        l = self.spline2.length(2/3)
        l_an = 0.5 * self.length2
        err = abs(l - l_an) / l_an
        assert err < 1e-7

        # Test zero length
        l = self.spline2.length(0.0)
        assert l == 0.0

        # Death tests
        assert_death(self.spline2.length, -0.01)
        assert_death(self.spline2.length, 1.01)


class TestCurveChain:
    def setup_method(self):
        self.crv1 = Segment((0, 0), (1, 0))
        self.crv2 = Segment((1, 0), (1, 1))
        self.crv3 = Segment((1, 1), (2, 1))
        self.chain = CurveChain([self.crv1, self.crv2, self.crv3])

    def test_geometry(self):
        # The chain should have 3 segments and 2 joints
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
        assert_vectors_equal(crv1.point(1), chain.point(l1/l), places=8)
        assert_vectors_equal(crv2.point(0), chain.point(l1/l), places=8)
        assert_vectors_equal(crv2.point(1), chain.point((l1 + l2)/l), places=8)
        assert_vectors_equal(crv3.point(0), chain.point((l1 + l2)/l), places=8)

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
        assert_vectors_equal(crv1.tangent(t), chain.tangent(t*l1/l), places=8)
        assert_vectors_equal(crv2.tangent(t),
                             chain.tangent((l1 + t*l2)/l), places=6)
        assert_vectors_equal(crv3.tangent(t),
                             chain.tangent((l1 + l2 + t*l3)/l), places=6)

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
        assert_vectors_equal(crv1.normal(t), chain.normal(t*l1/l))
        assert_vectors_equal(crv2.normal(t),
                             chain.normal((l1 + t*l2)/l))
        assert_vectors_equal(crv3.normal(t),
                             chain.normal((l1 + l2 + t*l3)/l))

    def test_length(self):
        # The total length should be the sum of the lengths of the curves
        l = self.chain.length(1.0)
        l1 = self.crv1.length(1.0)
        l2 = self.crv2.length(1.0)
        l3 = self.crv3.length(1.0)

        assert self.chain.length(0.0) == 0.0
        assert l == pytest.approx(l1 + l2 + l3)
        assert self.chain.length(l1/l) == pytest.approx(l1)
        assert self.chain.length((l1 + l2)/l) == pytest.approx(l1 + l2)

        # Death tests
        assert_death(self.chain.length, -0.01)
        assert_death(self.chain.length, 1.01)


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
