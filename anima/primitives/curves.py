from .object import BaseObject
from .attachments import BaseAttachment
from anima.globals.general import Vector, reciprocal
from abc import abstractmethod

DEFAULT_LINE_WIDTH = 0.02
NORMAL = DEFAULT_LINE_WIDTH
THIN = 0.5 * NORMAL
THICK = 1.5 * NORMAL

DEFAULT_DASH_LENGTH = 0.1
DEFAULT_GAP_LENGTH = 0.02


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
        self._attachment_0: type[BaseAttachment] = None
        self._attachment_1: type[BaseAttachment] = None
        self._length = 0.0
        self._length_inverse = 0.0

        # Store current length (need to manually update every time geometry is changed).
        self._update_length()

    def set_param_0(self, param: float):
        self._set_param(param, 0)

    def set_param_1(self, param: float):
        self._set_param(param, 1)

    def update_param_0(self):
        self.set_param_0(self._param_0)

    def update_param_1(self):
        self.set_param_1(self._param_1)

    def set_attachment_0(self, attmnt: type[BaseAttachment]):
        self._attachment_0 = attmnt
        self.update_param_0()
        from .endcaps import Endcap
        if isinstance(attmnt, Endcap):
            self._update_attachment_0()
        return self

    def set_attachment_1(self, attmnt: type[BaseAttachment]):
        self._attachment_1 = attmnt
        self.update_param_1()
        from .endcaps import Endcap
        if isinstance(attmnt, Endcap):
            self._update_attachment_1()
        return self

    def make_dashed(self, dash_len: float = DEFAULT_DASH_LENGTH, gap_len: float = DEFAULT_GAP_LENGTH,
                    offset: float = 0.0):
        pass

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
        raise Exception(f'Cannot yet compute curvature for curve {self.name}.')

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

    @property
    def attachment_0(self) -> float:
        """Get the curve's attachment_0."""
        return self._attachment_0

    @attachment_0.setter
    def attachment_0(self, attmnt: type[BaseAttachment]):
        """Set the curve's attachment_0."""
        self.set_attachment_0(attmnt)

    @property
    def attachment_1(self) -> float:
        """Get the curve's attachment_1."""
        return self._attachment_1

    @attachment_1.setter
    def attachment_1(self, attmnt: type[BaseAttachment]):
        """Set the curve's attachment_1."""
        self.set_attachment_1(attmnt)

    # Private methods -------------------------------------------------------------------------------------- #

    @abstractmethod
    def _set_param(self, param: float, end_idx: int):
        param_other = getattr(self, f'param_{1 - end_idx}')
        assert param >= param_other if end_idx == 1 else param <= param_other
        setattr(self, f'_param_{end_idx}', param)
        self._update_attachment(end_idx)

    def _set_both_params(self, param: float):
        self.set_param_0(param)
        self.set_param_1(param)

    @abstractmethod
    def _update_attachment(self, end_idx: int):
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

    def _compute_end_offset(self, end_idx: int, is_distance=False):
        attmt = getattr(self, f'_attachment_{end_idx}')
        mult = self._length_inverse if not is_distance else 1
        return mult * attmt.offset_distance() if attmt is not None else 0.0

    def _compute_end_offset_0(self, is_distance=False) -> float:
        return self._compute_end_offset(0, is_distance)

    def _compute_end_offset_1(self, is_distance=False) -> float:
        return self._compute_end_offset(1, is_distance)

    def _compute_offset_param(self, param: float, end_idx: int) -> float:
        # Compute end offsets.
        attmt = getattr(self, f'_attachment_{end_idx}')
        offs_0 = self._compute_end_offset(0, is_distance=False)
        offs_1 = self._compute_end_offset(1, is_distance=False)

        # If the attachment is a joint, only need to apply offset at the ends.
        from .joints import Joint
        if isinstance(attmt, Joint) and offs_0 < param < 1 - offs_1:
            offs_0 = offs_1 = 0

        return min(param + offs_0, 1.0 - offs_1) if end_idx == 0 else max(param - offs_1, offs_0)

    def _compute_offset_param_0(self, param: float) -> float:
        return self._compute_offset_param(param, 0)

    def _compute_offset_param_1(self, param: float) -> float:
        return self._compute_offset_param(param, 1)

    def _update_length(self):
        self._length = self.length()
        self._length_inverse = reciprocal(self._length)
