import math
from copy import deepcopy
from anima.globals.general import Vector
from .curves import BaseCurve, DEFAULT_LINE_WIDTH, DEFAULT_DASH_LENGTH, DEFAULT_GAP_LENGTH


class DashedCurve(BaseCurve):
    def __init__(self, curve: type[BaseCurve], width: float = DEFAULT_LINE_WIDTH, bias: float = 0.0,
                 dash_len: float = DEFAULT_DASH_LENGTH, gap_len: float = DEFAULT_GAP_LENGTH,
                 dash_offs: float = 0.0, name: str = 'DashedCurve'):

        self._dash_len = dash_len
        self._gap_len = gap_len
        # Recast offset to range [0, 1]. 1 unit ~ (dash_l + gap_l)
        assert abs(dash_offs) <= 1, "Dash offset must be in range [-1, 1]."
        self._dash_offs = dash_offs - math.floor(dash_offs)
        self._base_curve = curve
        self._dashes: list[type[BaseCurve]] = []

        curve.width = 0.1 * DEFAULT_LINE_WIDTH

        super().__init__(bl_object=None, width=width, bias=bias, name=name)
        self._construct()

        # Set width and bias
        self.set_width(width)
        self.set_bias(bias)

    def set_width(self, width: float):
        super().set_width(width)
        for c in self._dashes:
            c.set_width(width)

    def set_bias(self, bias: float):
        super().set_bias(bias)
        for c in self._dashes:
            c.set_bias(bias)

    def point(self, t: float) -> Vector:
        return self._base_curve.point(t)

    def tangent(self, t: float, normalise=False) -> Vector:
        return self._base_curve.tangent(t, normalise)

    def normal(self, t: float, normalise=False) -> Vector:
        return self._base_curve.normal(t, normalise)

    def length(self, t: float = 1.0) -> float:
        return self._base_curve.length(t)

    # Private methods -------------------------------------------------------------------------------------- #

    def _construct(self):
        # Compute t intervals corresponding to the dashes.
        tot_len = self._length
        inv_len = self._length_inverse
        dash = self._dash_len * inv_len
        gap = self._gap_len * inv_len
        stride = dash + gap
        offset = self._dash_offs * stride

        # t0 = stride % offset
        t0 = 0
        while t0 < tot_len:
            # Compute t1 and make a dash over the interval (t0, t1).
            t1 = min(t0 + dash, tot_len)
            crv = self._base_curve
            # crv = deepcopy(self._base_curve)
            crv.param_0 = t0
            crv.param_1 = t1
            self._dashes.append(crv)

            # Jump to the next dash.
            t0 += stride

    def _set_param(self, param: float, end_idx: int):
        super()._set_param(param, end_idx)

    def _update_attachment(self, end_idx: int):
        pass
