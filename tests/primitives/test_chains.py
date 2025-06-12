import pytest
from anima.primitives.chains import CurveChain
from anima.primitives.lines import Segment
from tests.test_utils import assert_death, assert_vectors_equal


class TestCurveChain:
    def setup_method(self):
        self.crv1 = Segment((0, 0), (1, 0))
        self.crv2 = Segment((1, 0), (1, 1))
        self.crv3 = Segment((1, 1), (2, 1))
        self.chain = CurveChain([self.crv1, self.crv2, self.crv3])

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
