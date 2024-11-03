from .object import BaseObject
from apeiron.globals.general import Vector, get_3d_vector, add_line_segment
from abc import abstractmethod

DEFAULT_LINE_WIDTH = 0.02


class BaseCurve(BaseObject):
    """
    Base class from which all curve objects will derive.
    """

    def __init__(self, name='BaseCurve', bl_object=None, width=DEFAULT_LINE_WIDTH, bias=0.0):
        super().__init__(name, bl_object)
        self.width = width

        self.set_width(width)
        self.set_bias(bias)

    def set_width(self, width):
        """Sets the width of the curve by setting a line segment as its profile, which is then swept along 
        the curve."""

        assert self.bl_obj is not None, 'The base object has not yet been set.'
        self.width = width

        profile = self.bl_obj.data.bevel_object
        hw = 0.5 * width
        pts = [(-hw, 0), (hw, 0)]  # Centred about the origin

        if profile is not None:
            bpts = profile.data.splines[0].bezier_points
            assert len(bpts) == 2, 'Expected a segment as the bevel profile.'
            for i, pt in enumerate(pts):
                bpts[i].co = get_3d_vector(pt)
        else:
            line_obj = add_line_segment('profile', *pts)
            self.bl_obj.data.bevel_mode = 'OBJECT'
            self.bl_obj.data.bevel_object = line_obj
            line_obj.parent = self.bl_obj

        # Set same width for all children
        for c in self.children:
            c.set_width(width)

    def set_bias(self, bias: float):
        """Sets a bias that offsets the curve from its centreline. A bias of 1 offsets the curve to the right 
        (when looking along the curve) by half the width, while a bias of -1 offsets it to the left by half 
        the width."""

        assert -1.0 <= bias <= 1.0, 'The bias must be in the range [-1, 1].'
        self.bl_obj.data.offset = -bias * (0.5 * self.width)

        # Set same bias for all children
        for c in self.children:
            c.set_bias(bias)

    @abstractmethod
    def point(self, t: float) -> Vector:
        """Computes the point on the curve associated to the paramater t."""
        pass

    @abstractmethod
    def tangent(self, t: float, normalise=False) -> Vector:
        """Computes the tangent of the curve associated to the paramater t."""
        pass

    @abstractmethod
    def normal(self, t: float, normalise=False) -> Vector:
        """Computes the normal of the curve associated to the paramater t."""
        pass

    @abstractmethod
    def length(self, t: float) -> float:
        """Computes the length along the curve up to the paramater t."""
        pass

    def curvature(self, t: float) -> float:
        """Computes the curvature of the curve at the paramater t."""
        raise Exception(f'Cannot compute curvature for curve {self.name}.')

    def binormal(self, t: float, normalise=False) -> Vector:
        """Computes the binormal of the curve associated to the paramater t."""
        tang = self.tangent(t, normalise)
        norm = self.normal(t, normalise)
        assert not (tang is None or norm is None)
        return tang.cross(norm)

    def velocity(self, t: float) -> Vector:
        """Computes the velocity of the curve associated to the paramater t."""
        return self.tangent(t, False)

    def speed(self, t: float) -> float:
        """Computes the speed of the curve associated to the paramater t."""
        return self.velocity(t).magnitude()
