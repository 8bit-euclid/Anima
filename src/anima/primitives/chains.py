import bisect
import math

from anima.globals.general import Vector, are_vectors_close, clip, reciprocal

from .curves import DEFAULT_LINE_WIDTH, Curve
from .joints import Joint, RoundJoint


class CurveChain(Curve):
    def __init__(
        self,
        curves: list[type[Curve]],
        width: float = DEFAULT_LINE_WIDTH,
        bias: float = 0.0,
        name: str = "CurveChain",
    ):
        """Initialise a CurveChain with a list of curves.

        Args:
            curves: A list of curves to be chained together.
            width: The width of the curve chain.
            bias: The bias of the curve chain.
            name: The name of the curve chain.
        """
        for c in curves:
            assert not isinstance(c, Joint), "The curves in a curve chain cannot be joints."
        self._curves: list[type[Curve]] = curves
        self._joints: list[type[Joint]] = []
        self._cumu_lengths: list[float] = []
        self._curve_0_idx: int = None
        self._curve_1_idx: int = None

        # Initialise joints.
        for curve_1, curve_2 in zip(curves, curves[1:]):
            assert are_vectors_close(
                curve_1.point(1), curve_2.point(0)
            ), f"The end-point of the first curve must be the start-point for the second."
            joint = RoundJoint(curve_1, curve_2)
            self._joints.append(joint)

        # Set indices of curves 0 and 1.
        self._curve_0_idx = 0
        self._curve_1_idx = len(self._all_entities) - 1

        super().__init__(width=width, bias=bias, name=name)

        # Add all entities as children of this object.
        for c in self._all_entities:
            self.add_subobject(c)

        # Set the width and bias.
        self.set_width(width)
        self.set_bias(bias)

    def set_width(self, width: float):
        """Set the width of the curve chain.

        Args:
            width: The width of the curve chain.
        """
        for c in self._all_entities:
            c.set_width(width)
        self._update_length()

    def set_bias(self, bias: float):
        """Set the bias of the curve chain.

        Args:
            bias: The bias of the curve chain.
        """
        for c in self._all_entities:
            c.set_bias(bias)
        self._update_length()

    def point(self, t: float) -> Vector:
        """Compute the point on the curve chain associated to the paramater t.

        Args:
            t: The parameter value.

        Returns:
            The point on the curve chain associated to the paramater t.
        """
        crv, _, t = self._compute_curve_info(t)
        return crv.point(t)

    def tangent(self, t: float, normalise=False) -> Vector:
        """Compute the tangent of the curve chain associated to the paramater t.

        Args:
            t: The parameter value.
            normalise: Whether to normalise the tangent.

        Returns:
            The tangent of the curve chain associated to the paramater t.
        """
        crv, _, t = self._compute_curve_info(t)
        return crv.tangent(t, normalise)

    def normal(self, t: float, normalise=False) -> Vector:
        """Compute the normal of the curve chain associated to the paramater t.

        Args:
            t: The parameter value.
            normalise: Whether to normalise the normal.

        Returns:
            The normal of the curve chain associated to the paramater t.
        """
        crv, _, t = self._compute_curve_info(t)
        return crv.normal(t, normalise)

    def length(self, t: float = 1.0) -> float:
        """Compute the length of the curve chain up to the paramater t.

        Args:
            t: The parameter value. Defaults to 1.0 (full length).

        Returns:
            The length of the curve chain up to the paramater t.
        """
        assert 0.0 <= t <= 1.0, f"Parameter must be in range [0, 1]. Got: {t:.3f}"
        return t * self._length

    # Private methods -------------------------------------------------------------------------------------- #
    @property
    def _all_entities(self) -> list[type[Curve]]:
        """Get the list of all entities in the curve chain (curves and joints).

        Returns:
            list[type[Curve]]: A list of all entities in the curve chain (curves and joints).
        """
        curves = self._curves
        joints = self._joints
        return [crv for pair in zip(curves, joints) for crv in pair] + curves[-1:]

    def _set_param(self, param: float, end_idx: int):
        """Set the parameter value for the start or end of the curve chain.

        Args:
            param: The parameter value.
            end_idx: The index of the end of the curve chain.
        """
        param_old = getattr(self, f"param_{end_idx}")
        super()._set_param(param, end_idx)

        crv_str = f"_curve_{end_idx}_idx"
        idx_ = getattr(self, crv_str)
        crv, idx, t = self._compute_curve_info(param)
        crv._set_param(t, end_idx)
        setattr(self, crv_str, idx)

        curves = self._all_entities
        if param < param_old:
            for c in curves[idx + 1 : idx_ + 1]:
                c._set_param(0, end_idx)
        else:
            for c in curves[idx_:idx]:
                c._set_param(1, end_idx)

    def _update_attachment(self, end_index: int):
        """Update the attachment at the specified end of the curve chain.

        Args:
            end_index: The index of the end of the curve chain.
        """
        # TODO: Implement attachment update for curve chains.
        super()._update_attachment(end_index)

    def _compute_curve_info(self, param: float) -> tuple[type[Curve], int, float]:
        """Compute the curve and parameter value associated to the paramater t.

        Args:
            param: The parameter value.

        Returns:
            A tuple containing the curve, its index, and the parameter value associated to the paramater t.
        """
        cumu_lens = self._cumu_lengths
        sz = len(cumu_lens)

        arc_len = param * self._length
        idx = bisect.bisect_left(cumu_lens, arc_len) - 1
        idx = clip(idx, 0, sz - 1)
        crv = self._all_entities[idx]

        end_offs = crv._compute_end_offset(0, is_distance=True)
        crv_param = (arc_len + end_offs - cumu_lens[idx]) * crv._length_inverse
        crv_param = clip(crv_param, 0, 1)
        return crv, idx, crv_param

    def _update_length(self):
        """Update the length, cumulative lengths, and inverse length of the curve chain after a change in width or bias."""

        # Compute and store curve lengths, cumulative lengths, and total length.
        curves = self._all_entities
        sz = len(curves)
        self._cumu_lengths = [0] * sz
        true_len = 0
        cumu_len = 0
        for i, c in enumerate(curves):
            # First update length of this curve.
            c._update_length()

            # Update true length (i.e. without joints).
            l = c._length
            if not isinstance(c, Joint):
                true_len += l

            # Subtract both end offset lengths from the curve length.
            for j in range(2):
                l -= c._compute_end_offset(j, is_distance=True)

            # Update cumulative length.
            self._cumu_lengths[i] = cumu_len
            cumu_len += l

        # Need to override super()._update_length() to avoid a cycle. This is because the latter invokes
        # self.length(), which requires self._length to have already been set.
        assert math.isclose(
            cumu_len, true_len, abs_tol=1e-6
        ), f"Inconsistent total length. Abs Error: {abs(cumu_len - true_len)}"
        self._length = cumu_len
        self._length_inverse = reciprocal(cumu_len)
