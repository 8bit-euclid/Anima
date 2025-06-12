import pytest
from anima.primitives.lines import Segment
from anima.primitives.joints import MiterJoint, BevelJoint, RoundJoint
from tests.test_utils import assert_death, assert_vector_equal


class TestJoint:
    def setup_method(self):
        self.crv1 = Segment((0, 0), (1, 0))
        self.crv2 = Segment((1, 0), (1, -1))
        self.miter = MiterJoint(self.crv1, self.crv2)
        self.bevel = BevelJoint(self.crv1, self.crv2)
        self.round = RoundJoint(self.crv1, self.crv2)

    def test_geometry(self):
        miter_verts = self.miter._vertices
        bevel_verts = self.bevel._vertices
        round_verts = self.round._vertices
        # ...add geometry assertions as needed...

    def test_point(self):
        miter = self.miter
        bevel = self.bevel
        round = self.round
        # ...add point assertions as needed...

    def test_tangent(self):
        pass

    def test_normal(self):
        pass

    def test_length(self):
        pass
