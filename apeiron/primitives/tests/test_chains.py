import unittest
from apeiron.primitives.chains import CurveChain
from apeiron.primitives.lines import Segment


class TestCurveChain(unittest.TestCase):
    def __init__(self, methodName="runTest"):
        super().__init__(methodName)

        self.crv1 = Segment((0, 0), (1, 0))
        self.crv2 = Segment((1, 0), (1, 1))
        self.crv3 = Segment((1, 1), (2, 1))

        self.chain = CurveChain([self.crv1, self.crv2, self.crv3])

    def assert_vector_equal(self, v1, v2, places=None):
        for i in range(len(v1)):
            self.assertAlmostEqual(v1[i], v2[i], places)

    def assert_death(self, func, *args, **kwargs):
        with self.assertRaises(AssertionError) as _:
            func(*args, **kwargs)

    def test_geometry(self):
        pass

    def test_point(self):
        pass

    def test_tangent(self):
        pass

    def test_normal(self):
        pass

    def test_length(self):
        pass


if __name__ == '__main__':
    unittest.main()
