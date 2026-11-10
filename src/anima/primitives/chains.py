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
        create_joints: bool = True,
        name: str = "CurveChain",
    ):
        """Initialise a CurveChain with a list of curves.

        Args:
            curves: A list of curves to be chained together.
            width: The width of the curve chain.
            bias: The bias of the curve chain.
            create_joints: Whether to create joints between curves. Defaults to False
                as joints are visually subtle but computationally expensive.
            name: The name of the curve chain.
        """
        for c in curves:
            assert not isinstance(c, Joint), "The curves in a curve chain cannot be joints."
        self._curves: list[type[Curve]] = curves
        self._joints: list[type[Joint]] = []
        self._cumu_lengths: list[float] = []
        self._curve_0_idx: int = None
        self._curve_1_idx: int = None

        # Validate curve connectivity and optionally create joints.
        for curve_1, curve_2 in zip(curves, curves[1:]):
            assert are_vectors_close(curve_1.point(1), curve_2.point(0)), (
                "The end-point of the first curve must be the start-point for the second."
            )
            if create_joints:
                joint = RoundJoint(curve_1, curve_2)
                self._joints.append(joint)

        # Set indices of curves 0 and 1.
        self._curve_0_idx = 0
        self._curve_1_idx = len(self._all_entities) - 1

        super().__init__(width=width, bias=bias, name=name)

        # Add all entities (curves and joints) as children of this object.
        for c in self._all_entities:
            self.add_child(c)

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

    @property
    def curves(self) -> list[type[Curve]]:
        """Get the list of curves in the curve chain (excluding joints).

        Returns:
            list[type[Curve]]: A list of curves in the curve chain.
        """
        return self._curves

    # Private methods -------------------------------------------------------------------------------------- #
    @property
    def _all_entities(self) -> list[type[Curve]]:
        """Get the list of all entities in the curve chain (curves and joints).

        Returns:
            list[type[Curve]]: A list of all entities in the curve chain (curves and joints).
        """
        curves = self._curves
        joints = self._joints
        if not joints:
            return curves
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

        if self.debug():
            self.validate_param_state()

    def validate_param_state(self, tol: float = 1e-6) -> None:
        """Assert that the children's parameters agree with the chain's `param_0` and `param_1`.

        `_set_param` only sweeps the curves between the previous and the new curve index, so it relies on
        every other child already being settled. For each end, children before the chain's current curve
        index must be at 1, children after it at 0, and the child at the index at the local parameter. This
        breaks if a child is modified directly, or if lengths change after construction. Joints are skipped
        because their own `_set_param` overwrites the opposite end's parameter. Called
        automatically after every parameter change while debugging is on (see `Object.debug_on`).

        Args:
            tol: The absolute tolerance used when comparing parameters.

        Raises:
            AssertionError: If a child's parameter, or the stored curve index, is inconsistent.
        """
        entities = self._all_entities
        for end_idx in (0, 1):
            param = getattr(self, f"_param_{end_idx}")
            _, expected_idx, expected_t = self._compute_curve_info(param)
            idx = getattr(self, f"_curve_{end_idx}_idx")
            assert idx == expected_idx, (
                f"{self.name}: stored curve index {idx} for end {end_idx} does not match the index "
                f"{expected_idx} implied by param {param}."
            )
            for i, c in enumerate(entities):
                if isinstance(c, Joint):
                    continue
                expected = 1.0 if i < idx else 0.0 if i > idx else expected_t
                actual = getattr(c, f"_param_{end_idx}")
                assert abs(actual - expected) <= tol, (
                    f"{self.name}: child {i} has param_{end_idx}={actual}, expected {expected}."
                )

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
        assert math.isclose(cumu_len, true_len, abs_tol=1e-6), (
            f"Inconsistent total length. Abs Error: {abs(cumu_len - true_len)}"
        )
        self._length = cumu_len
        self._length_inverse = reciprocal(cumu_len)

    @classmethod
    def from_svg_path(
        cls,
        path,
        create_joints: bool = False,
        name: str = "CurveChain",
        **kwargs,
    ):
        """Create a CurveChain from an SVG path.

        Args:
            path: An svgpathtools.Path object.
            create_joints: Whether to create joints between curves.
            name: The name of the curve chain.
            **kwargs: Additional keyword arguments passed to the constructor.

        Returns:
            A new CurveChain instance.
        """
        from anima.primitives.svg_utils import svg_path_to_curves

        curves = svg_path_to_curves(path, reverse=False)
        return cls(curves=curves, create_joints=create_joints, name=name, **kwargs)


class CurveLoop(CurveChain):
    """A closed curve chain where the last curve connects back to the first.

    Used for representing closed paths like glyph subpath borders. Inherits all
    functionality from CurveChain but validates closure and optionally adds a
    closing joint between the last and first curves. Its endpoint parameters may
    be unwrapped beyond [0, 1]; the visible interval then wraps around the loop.
    """

    def __init__(
        self,
        curves: list[type[Curve]],
        width: float = DEFAULT_LINE_WIDTH,
        bias: float = 0.0,
        create_joints: bool = False,
        name: str = "CurveLoop",
    ):
        """Initialise a CurveLoop with a list of curves forming a closed loop.

        Args:
            curves: A list of curves to be chained together in a closed loop.
            width: The width of the curve loop.
            bias: The bias of the curve loop.
            create_joints: Whether to create joints between curves. Defaults to False.
            name: The name of the curve loop.

        Raises:
            AssertionError: If the curves do not form a closed loop.
        """
        # Validate closure: last endpoint must match first startpoint
        if curves:
            assert are_vectors_close(curves[-1].point(1), curves[0].point(0)), (
                "CurveLoop must be closed: last curve endpoint must match first curve startpoint"
            )

        super().__init__(
            curves=curves,
            width=width,
            bias=bias,
            create_joints=create_joints,
            name=name,
        )

        # Add closing joint between last and first curve if requested
        if create_joints and len(curves) > 1:
            closing_joint = RoundJoint(curves[-1], curves[0])
            closing_joint.set_width(width)
            closing_joint.set_bias(bias)
            self._joints.append(closing_joint)
            self.add_child(closing_joint)
            self._curve_0_idx = 0
            self._curve_1_idx = len(self._all_entities) - 1
            self._update_length()
        self._apply_loop_params()

    def set_width(self, width: float):
        """Set loop width and restore joint visibility for the current parameter interval."""
        super().set_width(width)
        self._apply_loop_params()

    def set_bias(self, bias: float):
        """Set loop bias and restore joint visibility for the current parameter interval."""
        super().set_bias(bias)
        self._apply_loop_params()

    @property
    def _all_entities(self) -> list[type[Curve]]:
        """Return loop curves interleaved with their joints, including the closing joint."""
        entities = []
        for i, curve in enumerate(self._curves):
            entities.append(curve)
            if i < len(self._joints):
                entities.append(self._joints[i])
        return entities

    def _compute_curve_info(self, param: float) -> tuple[type[Curve], int, float]:
        """Map any parameter to a location on the closed loop, wrapping by one turn."""
        wrapped_param = param if 0.0 < param <= 1.0 else param % 1.0
        return super()._compute_curve_info(wrapped_param)

    def _set_param(self, param: float, end_idx: int):
        """Set an unwrapped endpoint and update the loop's visible curve segment."""
        Curve._set_param(self, param, end_idx)
        _, idx, _ = self._compute_curve_info(param)
        setattr(self, f"_curve_{end_idx}_idx", idx)
        self._apply_loop_params()
        if self.debug():
            self.validate_param_state()

    def _loop_curve_params(self) -> dict[int, tuple[float, float]]:
        """Return each curve's local visible interval for the current loop endpoints."""
        curves = self._curves
        if not curves:
            return {}

        total_length = sum(curve._length for curve in curves)
        if total_length <= 0.0:
            return {i: (0.0, 0.0) for i in range(len(curves))}

        delta = self._param_1 - self._param_0
        if delta == 0.0:
            span = 0.0
        elif abs(delta) >= 1.0:
            span = 1.0
        else:
            span = delta % 1.0

        if span == 0.0:
            return {i: (0.0, 0.0) for i in range(len(curves))}
        if span == 1.0:
            return {i: (0.0, 1.0) for i in range(len(curves))}

        start = self._param_0 % 1.0
        result = {}
        curve_start = 0.0
        for i, curve in enumerate(curves):
            curve_end = curve_start + curve._length / total_length
            overlaps = []
            for offset in (-1.0, 0.0):
                overlap_start = max(curve_start, start + offset)
                overlap_end = min(curve_end, start + span + offset)
                if overlap_end > overlap_start:
                    overlaps.append(
                        (
                            (overlap_start - curve_start) * total_length / curve._length,
                            (overlap_end - curve_start) * total_length / curve._length,
                        )
                    )

            if overlaps:
                result[i] = (max(0.0, overlaps[0][0]), min(1.0, overlaps[-1][1]))
            else:
                result[i] = (0.0, 0.0)
            curve_start = curve_end
        return result

    def _loop_joint_visibility(self) -> list[bool]:
        """Return whether each joint's corner lies inside the visible loop interval."""
        curves = self._curves
        if not self._joints or not curves:
            return []

        delta = self._param_1 - self._param_0
        if delta == 0.0:
            return [False] * len(self._joints)
        if abs(delta) >= 1.0:
            return [True] * len(self._joints)

        span = delta % 1.0
        total_length = sum(curve._length for curve in curves)
        if total_length <= 0.0:
            return [False] * len(self._joints)
        start = self._param_0 % 1.0
        visibility = []
        boundary = 0.0
        for i in range(len(self._joints)):
            boundary += curves[i]._length / total_length
            distance = (boundary - start) % 1.0
            visibility.append(distance <= span or math.isclose(distance, span, abs_tol=1e-9))
        return visibility

    def _apply_loop_params(self) -> None:
        """Apply the visible interval to child curves and joints."""
        params = self._loop_curve_params()
        for i, curve in enumerate(self._curves):
            start, end = params[i]
            curve._set_param(start, 0)
            curve._set_param(end, 1)
        for joint, visible in zip(self._joints, self._loop_joint_visibility()):
            face_count = len(joint.object.data.polygons)
            if visible and face_count != len(joint._frame_faces):
                joint.set_mesh(joint._frame_points, joint._frame_faces)
            elif not visible and face_count:
                joint.set_mesh([], [])

    def validate_param_state(self, tol: float = 1e-6) -> None:
        """Assert that child curve parameters match the loop's wrapped visible interval."""
        for i, curve in enumerate(self._curves):
            expected_start, expected_end = self._loop_curve_params()[i]
            for end_idx, expected in enumerate((expected_start, expected_end)):
                actual = getattr(curve, f"_param_{end_idx}")
                assert abs(actual - expected) <= tol, (
                    f"{self.name}: child {i} has param_{end_idx}={actual}, expected {expected}."
                )

    @property
    def closed(self) -> bool:
        """Returns True since CurveLoop is always closed."""
        return True

    @classmethod
    def from_svg_path(
        cls,
        path,
        create_joints: bool = False,
        name: str = "CurveLoop",
        **kwargs,
    ):
        """Create a CurveLoop from an SVG path.

        Args:
            path: A closed svgpathtools.Path object.
            create_joints: Whether to create joints between curves.
            name: The name of the curve loop.
            **kwargs: Additional keyword arguments passed to the constructor.

        Returns:
            A new CurveLoop instance.

        Raises:
            AssertionError: If the path is not closed.
        """
        assert path.isclosed(), "Path must be closed to create a CurveLoop"
        # Use parent's from_svg_path but with the CurveLoop class
        return super().from_svg_path(path, create_joints=create_joints, name=name, **kwargs)
