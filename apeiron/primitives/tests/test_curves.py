import unittest
import random
from apeiron.globals.general import Vector
from apeiron.primitives.bezier import BezierSpline


class TestBezier(unittest.TestCase):
    def __init__(self, methodName="runTest"):
        super().__init__(methodName)

        self.spline1 = BezierSpline([(0, 0), (3, 1), (7, -1)])
        self.spline1.set_resolution(100)
        self.spline1.set_left_handle(2, (-2.0, 0))

        self.length2 = 6
        self.spline2 = BezierSpline(
            [(0, 0), (1, 0), (3, 0), (self.length2, 0)])

    def assert_vector_equal(self, v1, v2, places=None):
        for i in range(len(v1)):
            self.assertAlmostEqual(v1[i], v2[i], places)

    def assert_death(self, func, *args, **kwargs):
        with self.assertRaises(AssertionError) as _:
            func(*args, **kwargs)

    def test_point(self):
        # Left endpoint (length factor parameter)
        pt = self.spline1.point(0.0)
        bpt = self.spline1.spline_point(0).co
        self.assert_vector_equal(pt, bpt)

        # Left endpoint (spline parameter)
        pt = self.spline1.point(0.0, is_len_factor=False)
        self.assert_vector_equal(pt, bpt)

        # Right endpoint (length factor parameter)
        pt = self.spline1.point(1.0)
        bpt = self.spline1.spline_point(2).co
        self.assert_vector_equal(pt, bpt)

        # Right endpoint (spline parameter)
        pt = self.spline1.point(1.0, is_len_factor=False)
        self.assert_vector_equal(pt, bpt)

        # Death tests
        self.assert_death(self.spline1.point, -0.1)
        self.assert_death(self.spline1.point, 1.1)

    def test_tangent(self):
        # Left endpoint tangent (length factor parameter)
        tn = self.spline1.tangent(0.0, normalise=True)
        spt = self.spline1.spline_point(0)
        bpt = spt.co
        hnd = spt.handle_right
        btn = (hnd - bpt).normalized()
        self.assert_vector_equal(tn, btn, places=6)

        # Left endpoint tangent (spline parameter)
        tn = self.spline1.tangent(0.0, normalise=True, is_len_factor=False)
        spt = self.spline1.spline_point(0)
        bpt = spt.co
        hnd = spt.handle_right
        btn = (hnd - bpt).normalized()
        self.assert_vector_equal(tn, btn, places=6)

        # Right endpoint tangent (length factor parameter). Should be horizontal.
        tn = self.spline1.tangent(1.0, normalise=True)
        btn = Vector((1, 0, 0))
        self.assert_vector_equal(tn, btn)

        # Right endpoint tangent (spline parameter). Should be horizontal.
        tn = self.spline1.tangent(1.0, normalise=True, is_len_factor=False)
        self.assert_vector_equal(tn, btn)

        # Death tests
        self.assert_death(self.spline1.tangent, -0.1)
        self.assert_death(self.spline1.tangent, 1.1)

    def test_normal(self):
        # Add enpoint params and generate random intermediate params.
        params = [0, 1]
        for i in range(100):
            params.append(random.random())

        # Test orthogonality of normal and tangent at each param.
        for t in params:
            # length factor parameter
            nm = self.spline1.normal(t)
            tn = self.spline1.tangent(t)
            self.assertAlmostEqual(nm.dot(tn), 0)

            # spline parameter
            nm = self.spline1.normal(t, is_len_factor=False)
            tn = self.spline1.tangent(t, is_len_factor=False)
            self.assertAlmostEqual(nm.dot(tn), 0)

        # Death tests
        self.assert_death(self.spline1.normal, -0.1)
        self.assert_death(self.spline1.normal, 1.1)

    def test_length(self):
        # Test total length
        l = self.spline2.length(1.0)
        self.assertAlmostEqual(l, self.length2, places=7)

        # Test half length (spline param of 2/3)
        l = self.spline2.length(2/3)
        self.assertAlmostEqual(l, 0.5*self.length2, places=7)

        # Test zero length
        l = self.spline2.length(0.0)
        self.assertEqual(l, 0.0)


if __name__ == '__main__':
    unittest.main()
