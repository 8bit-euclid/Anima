import unittest
from apeiron.primitives.lines import Segment
from apeiron.primitives.joints import MiterJoint, BevelJoint, RoundJoint


class TestJoint(unittest.TestCase):
    def __init__(self, methodName="runTest"):
        super().__init__(methodName)

        self.crv1 = Segment((0, 0), (1, 0))
        self.crv2 = Segment((1, 0), (1, -1))

        self.miter = MiterJoint(self.crv1, self.crv2)
        self.bevel = BevelJoint(self.crv1, self.crv2)
        self.round = RoundJoint(self.crv1, self.crv2)

    def assert_vector_equal(self, v1, v2, places=None):
        for i in range(len(v1)):
            self.assertAlmostEqual(v1[i], v2[i], places)

    def assert_death(self, func, *args, **kwargs):
        with self.assertRaises(AssertionError) as _:
            func(*args, **kwargs)

    def test_geometry(self):
        miter_verts = self.miter._vertices
        bevel_verts = self.bevel._vertices
        round_verts = self.round._vertices

    def test_point(self):
        miter = self.miter
        bevel = self.bevel
        round = self.round

    def test_tangent(self):
        pass

    def test_normal(self):
        pass

    def test_length(self):
        pass


if __name__ == '__main__':
    unittest.main()
