from .object import BaseObject
from .attachments import BaseAttachment
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

    def __init__(self, bl_object=None, width: float = DEFAULT_LINE_WIDTH, bias: float = 0.0,
                 name: str = 'BaseCurve', **kwargs):
        super().__init__(bl_object=bl_object, name=name, **kwargs)

        self._width = width
        self._bias = bias
        self._param_0 = 0.0
        self._param_1 = 1.0
        self._attachment_0: BaseAttachment = None
        self._attachment_1: BaseAttachment = None
        self._length = 0.0

        # Store current length (need to manually update every time geometry is changed).
        self._store_length()

    def set_param_0(self, param: float):
        self._set_param(param, 0)

    def set_param_1(self, param: float):
        self._set_param(param, 1)

    def update_param_0(self):
        self.set_param_0(self._param_0)

    def update_param_1(self):
        self.set_param_1(self._param_1)

    def set_attachment_0(self, attmnt: BaseAttachment):
        self._attachment_0 = attmnt
        self.update_param_0()
        from .endcaps import Endcap
        if isinstance(attmnt, Endcap):
            self._update_attachment_0()
        return self

    def set_attachment_1(self, attmnt: BaseAttachment):
        self._attachment_1 = attmnt
        self.update_param_1()
        from .endcaps import Endcap
        if isinstance(attmnt, Endcap):
            self._update_attachment_1()
        return self

    @abstractmethod
    def set_width(self, width: float):
        """Sets the width of the curve by setting a line segment as its profile, which is then swept along 
        the curve."""
        self._width = width

    @abstractmethod
    def set_bias(self, bias: float):
        """Sets a bias that offsets the curve from its centreline. A bias of 1 offsets the curve to the right 
        (when looking along the tangent of the curve) by half the width, while a bias of -1 offsets it to the 
        left by half the width."""
        self._bias = bias

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

    # Property getters/setters ----------------------------------------------------------------------------- #
    @property
    def width(self) -> float:
        """Get the curve's width."""
        return self._width

    @width.setter
    def width(self, w: float):
        """Set the curve's width."""
        self.set_width(w)

    @property
    def bias(self) -> float:
        """Get the curve's bias."""
        return self._bias

    @bias.setter
    def bias(self, b: float):
        """Set the curve's bias."""
        assert -1.0 <= b <= 1.0, 'The bias must be in the range [-1, 1].'
        self.set_bias(b)

    @property
    def param_0(self) -> float:
        """Get the curve's param_0."""
        return self._param_0

    @param_0.setter
    def param_0(self, param: float):
        """Set the curve's param_0."""
        self.set_param_0(param)

    @property
    def param_1(self) -> float:
        """Get the curve's param_1."""
        return self._param_1

    @param_1.setter
    def param_1(self, param: float):
        """Set the curve's param_1."""
        self.set_param_1(param)

    # Private methods -------------------------------------------------------------------------------------- #
    @abstractmethod
    def _set_param(self, param: float, end_index: int):
        if end_index == 0:
            self._param_0 = param
        else:
            self._param_1 = param

        self._update_attachment(end_index)

    @abstractmethod
    def _update_attachment(self, end_index: int):
        pass

    def _attachments(self):
        return [self._attachment_0, self._attachment_1]

    def _update_attachment_0(self):
        self._update_attachment(0)

    def _update_attachment_1(self):
        self._update_attachment(1)

    def _update_attachments(self):
        self._update_attachment_0()
        self._update_attachment_1()

    def _compute_offset_param_0(self, param: float):
        attmt = self._attachment_0
        offset = (attmt.offset_distance() /
                  self._length) if attmt is not None else 0.0
        return min(param + offset, 1.0)

    def _compute_offset_param_1(self, param: float):
        attmt = self._attachment_1
        offset = (attmt.offset_distance() /
                  self._length) if attmt is not None else 0.0
        return max(param - offset, 0.0)

    def _store_length(self):
        self._length = self.length()

    def _update_length(self):
        self._store_length()
