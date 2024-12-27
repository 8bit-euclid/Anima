import math
import copy
import bisect
from typing import List, Tuple
from .curves import BaseCurve, DEFAULT_LINE_WIDTH
from .joints import Joint, RoundJoint, DEFAULT_LINE_WIDTH
from apeiron.globals.general import Vector, are_vectors_close, reciprocal, clip


class CurveChain(BaseCurve):
    def __init__(self, curves: List[BaseCurve], width: float = DEFAULT_LINE_WIDTH, bias: float = 0.0,
                 name: str = 'CurveChain'):
        self._curves: List[BaseCurve] = curves
        self._joints: List[Joint] = []
        self._all_curves: List[BaseCurve] = []
        self._cumu_lengths: List[float] = []
        self._curve_0_idx: int = None
        self._curve_1_idx: int = None

        # Initialise joints and order all curves.
        for curve_1, curve_2 in zip(curves, curves[1:]):
            assert are_vectors_close(curve_1.point(1), curve_2.point(0)), \
                "The end-point of the first curve must be the start-point for the second"
            joint = RoundJoint(curve_1, curve_2)
            # joint = Joint(curve_1, curve_2)
            self._joints.append(joint)
            self._all_curves.extend([curve_1, joint])

        self._all_curves.append(curves[-1])

        # Set indices of curves 0 and 1.
        self._curve_0_idx = 0
        self._curve_1_idx = len(self._all_curves) - 1

        # Set the width and bias.
        self.set_width(width)
        self.set_bias(bias)

        super().__init__(width=width, bias=bias, name=name)

    def set_width(self, width: float):
        for c in self._all_curves:
            c.set_width(width)
        self._update_length()

    def set_bias(self, bias: float):
        for c in self._all_curves:
            c.set_bias(bias)
        self._update_length()

    def point(self, t: float) -> Vector:
        crv, _, t = self._compute_curve_info(t)
        return crv.point(t)

    def tangent(self, t: float, normalise=False) -> Vector:
        crv, _, t = self._compute_curve_info(t)
        return crv.tangent(t, normalise)

    def normal(self, t: float, normalise=False) -> Vector:
        crv, _, t = self._compute_curve_info(t)
        return crv.normal(t, normalise)

    def length(self, t: float = 1.0) -> float:
        crv, idx, t = self._compute_curve_info(t)
        cumu_len = self._cumu_lengths[idx]
        return cumu_len + crv.length(t)

    # Private methods -------------------------------------------------------------------------------------- #

    def _set_param(self, param: float, end_idx: int):
        param_old = getattr(self, f'param_{end_idx}')
        super()._set_param(param, end_idx)

        crv_str = f'_curve_{end_idx}_idx'
        idx_ = getattr(self, crv_str)
        crv, idx, t = self._compute_curve_info(param)
        crv._set_param(t, end_idx)
        setattr(self, crv_str, idx)

        curves = self._all_curves
        if param < param_old:
            for c in curves[idx + 1: idx_ + 1]:
                c._set_param(0, end_idx)
        else:
            for c in curves[idx_: idx]:
                c._set_param(1, end_idx)

    def _update_attachment(self, end_index: int):
        # todo
        super()._update_attachment(end_index)

    def _compute_curve_info(self, param: float) -> Tuple[BaseCurve, int, float]:
        cumu_lens = self._cumu_lengths
        sz = len(cumu_lens)

        arc_len = param * self._length
        idx = bisect.bisect_left(cumu_lens, arc_len) - 1
        idx = clip(idx, 0, sz - 1)
        crv: BaseCurve = self._all_curves[idx]

        end_offs = crv._compute_end_offset(0, is_distance=True)
        if crv._write_logs:
            print(arc_len, end_offs, cumu_lens[idx])
        crv_param = (arc_len + end_offs - cumu_lens[idx]) * \
            crv._length_inverse
        crv_param = clip(crv_param, 0, 1)
        return crv, idx, crv_param

    def _update_length(self):
        # Compute and store curve lengths, cumulative lengths, and total length.
        sz = len(self._all_curves)
        self._cumu_lengths = [0] * sz
        cumu_len = 0
        for i, c in enumerate(self._all_curves):
            # First update length of this curve.
            c._update_length()

            # Compute curve length and subtract both end offset lengths.
            l = copy.deepcopy(c._length)
            for j in range(2):
                l -= c._compute_end_offset(j, is_distance=True)

            self._cumu_lengths[i] = cumu_len
            cumu_len += l

        # Need to explicitly calculate own length and inverse length
        # instead of invoking super()._update_length()
        self._length = cumu_len
        self._length_inverse = reciprocal(cumu_len)
