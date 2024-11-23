from .object import BaseObject
from apeiron.globals.general import Vector
from abc import abstractmethod

DEFAULT_LINE_WIDTH = 0.02
NORMAL = DEFAULT_LINE_WIDTH
THIN = 0.5 * NORMAL
THICK = 1.5 * NORMAL


class BaseCurve(BaseObject):
    """
    Base class from which all curve objects will derive.
    """

    def __init__(self, bl_object, name='BaseCurve', width=DEFAULT_LINE_WIDTH, bias=0.0):
        super().__init__(bl_object, name)
        self.width = width
        self.attachment_0: BaseObject = None
        self.attachment_1: BaseObject = None
        self.offset_0: float = 0.0
        self.offset_1: float = 0.0

        self.set_width(width)\
            .set_bias(bias)

    def set_attachment_0(self, attmnt):
        self.attachment_0 = attmnt
        self.offset_0 = attmnt.offset_length() / self.length()
        t = 0.0
        attmnt.location = self.point(t)
        attmnt.set_orientation(self.normal(t), -self.tangent(t))
        return self

    def set_attachment_1(self, attmnt):
        self.attachment_1 = attmnt
        self.offset_1 = attmnt.offset_length() / self.length()
        t = 1.0
        attmnt.location = self.point(t)
        attmnt.set_orientation(-self.normal(t), self.tangent(t))
        return self

    @abstractmethod
    def set_width(self, width: float):
        """Sets the width of the curve by setting a line segment as its profile, which is then swept along 
        the curve."""
        pass

    @abstractmethod
    def set_bias(self, bias: float):
        """Sets a bias that offsets the curve from its centreline. A bias of 1 offsets the curve to the right 
        (when looking along the tangent of the curve) by half the width, while a bias of -1 offsets it to the 
        left by half the width."""
        pass

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
    def length(self, t: float = 1.0) -> float:
        """Computes the length along the curve up to the paramater t."""
        pass

    def curvature(self, t: float) -> float:
        """Computes the curvature of the curve at the paramater t."""
        raise Exception(f'Cannot compute curvature for curve {self.name}.')

    def binormal(self, t: float, normalise=False) -> Vector:
        """Computes the binormal of the curve associated to the paramater t."""
        tang = self.tangent(t, normalise)
        norm = self.normal(t, normalise)
        return tang.cross(norm)
