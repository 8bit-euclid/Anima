import math
from copy import deepcopy
from dataclasses import dataclass, field
from functools import partial

from anima.globals.general import Vector, clip
from anima.primitives.chains import CurveChain
from anima.primitives.joints import Joint

from .curves import DEFAULT_DASH_LENGTH, DEFAULT_GAP_LENGTH, DEFAULT_LINE_WIDTH, Curve


class DashedCurve(Curve):
    @dataclass
    class Dash:
        curve: type[Curve] = field(default=None)
        ref_param_0: float = field(default=0.0)
        ref_param_1: float = field(default=0.0)

    def __init__(
        self,
        curve: type[Curve],
        width: float = DEFAULT_LINE_WIDTH,
        bias: float = 0.0,
        dash_len: float = DEFAULT_DASH_LENGTH,
        gap_len: float = DEFAULT_GAP_LENGTH,
        offset: float = 0.0,
        name: str = "DashedCurve",
    ):
        self._base_curve = curve
        self._dash_len = dash_len
        self._gap_len = gap_len
        self._offset = self._normalised_offset(offset)
        self._dashes: list[DashedCurve.Dash] = []

        # Initialise Curve and store length.
        super().__init__(width=width, bias=bias, name=name)
        self._update_geometry()

        # Hide base curve.
        curve.hide()

    def auto_adjust(self):
        pass

    def set_width(self, width: float):
        super().set_width(width)
        for d in self._dashes:
            d.curve.width = width

    def set_bias(self, bias: float):
        super().set_bias(bias)
        for d in self._dashes:
            d.curve.bias = bias

    def set_offset(self, offs: float):
        """Set the curve's dash offset."""
        self._offset = self._normalised_offset(offs)
        self._update_param_0()
        self._update_param_1()

    def point(self, t: float) -> Vector:
        return self._base_curve.point(t)

    def tangent(self, t: float, normalise=False) -> Vector:
        return self._base_curve.tangent(t, normalise)

    def normal(self, t: float, normalise=False) -> Vector:
        return self._base_curve.normal(t, normalise)

    def length(self, t: float = 1.0) -> float:
        return self._base_curve.length(t)

    # Property getters/setters ----------------------------------------------------------------------------- #

    @property
    def offset(self) -> float:
        """Get the curve's dash offset."""
        return self._width

    @offset.setter
    def offset(self, offs: float):
        """Set the curve's dash offset."""
        self.set_offset(offs)

    @property
    def _stride(self) -> float:
        """Get the curve's dash stride (dash_l + gap_l) / l."""
        return (self._dash_len + self._gap_len) * self._length_inverse

    # Private methods -------------------------------------------------------------------------------------- #

    def _normalised_offset(self, offs: float) -> float:
        # Recast offset to range [0, 1]. 1 unit ~ (dash_l + gap_l)
        return offs - math.floor(offs)

    def _update_geometry(self):
        self._check_dash_len(self._base_curve)

        # Compute t intervals corresponding to the dashes.
        inv_len = self._length_inverse
        dash_dt = self._dash_len * inv_len
        gap_dt = self._gap_len * inv_len
        stride_dt = dash_dt + gap_dt
        offset_dt = self._offset * stride_dt

        num_dashes = math.ceil(1.0 / stride_dt) + 1
        num_new = max(0, num_dashes - len(self._dashes))
        if num_new > 0:
            self._dashes.extend([None] * num_new)

        clip_param = partial(clip, min_val=0, max_val=1)
        dashes = self._dashes
        for i, dash in enumerate(dashes):
            # Create the curve for the dash, if necessary.
            if dash is None:
                dash = DashedCurve.Dash()
                dashes[i] = dash
                dash.curve = deepcopy(self._base_curve)

            # Compute and make a dash over the interval (t0, t1).
            t0 = (i - 1) * stride_dt  # Start with hidden dash.
            t1 = t0 + dash_dt
            dash.ref_param_0 = t0
            dash.ref_param_1 = t1

            # Set relevant curve attributes.
            crv = dash.curve
            crv.width = self.width
            crv.bias = self.bias
            crv.param_0 = clip_param(t0 + offset_dt)
            crv.param_1 = clip_param(t1 + offset_dt)

        # Add all new dash curves as children of this object.
        if num_new > 0:
            for d in dashes[-num_new:]:
                self.add_subobject(d.curve)

        # Todo - remove any extra dash curves.

    def _check_dash_len(self, crv: type[Curve]):
        # If joints exist, ensure that the dash length is not smaller than any of them.
        if isinstance(crv, CurveChain):
            for c in crv._all_entities:
                self._check_dash_len(c)
        elif isinstance(crv, Joint):
            assert (
                crv._length <= self._dash_len
            ), "Dash length must be greater than the largest joint length."

    def _set_param(self, param: float, end_idx: int):
        super()._set_param(param, end_idx)

        offset_dt = self._offset * self._stride
        for d in self._dashes:
            # Compute the offset reference parameters.
            ref_0 = clip(d.ref_param_0 + offset_dt, 0, 1)
            ref_1 = clip(d.ref_param_1 + offset_dt, 0, 1)

            # Update the dash curve's parameters.
            crv = d.curve
            if end_idx == 0:
                upper = min(clip(crv.param_1, ref_0, ref_1), ref_1)
                crv.param_0 = clip(param, ref_0, upper)
            else:
                lower = max(clip(crv.param_0, ref_0, ref_1), ref_0)
                crv.param_1 = clip(param, lower, ref_1)

    def _update_attachment(self, end_idx: int):
        pass
