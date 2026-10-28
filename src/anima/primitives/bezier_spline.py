from __future__ import annotations

import math
from array import array
from collections.abc import Iterable
from typing import Any

import bpy
import numpy as np
import numpy.typing as npt
from scipy import integrate

from anima.globals.general import (
    Vector,
    add_line_segment,
    add_object,
    deepcopy_object,
    disable_print,
    enable_print,
    make_3d_vector,
    rotate_90,
)

from .curves import DEFAULT_LINE_WIDTH, Curve
from .endcaps import Endcap

DEFAULT_RESOLUTION = 100
RELATIVE_LENGTH_ERR = 1.0e-4  # 0.01% of the length
MIN_ABSOLUTE_LENGTH_ERR = 1.0e-5
NUM_PARAM_LOOKUP_PTS = 40
NUM_GAUSS_NODES = 128
_GAUSS_LEGENDRE = np.polynomial.legendre.leggauss(NUM_GAUSS_NODES)
Coefficients = tuple[float, float, float]


class BezierSpline(Curve):
    """A Blender-backed spline composed of connected cubic Bezier segments.

    The spline points are anchors; each segment uses the right handle of its
    first anchor and the left handle of its second. The spline parameter spans
    [0, 1], with an equal interval for each segment. In contrast, ``point``,
    ``tangent`` and ``normal`` accept a fraction of the total arc length.
    ``length`` accepts the spline parameter rather than an arc-length fraction.

    Lengths are computed by numerical integration. Conversion from arc length
    to spline parameter uses a sampled lookup table with linear interpolation,
    built on first use. Geometry updates invalidate the table; unchanged geometry
    reuses the cached lengths. If Blender spline data is edited directly, call
    ``_update_length()`` before using length-dependent operations.
    """

    def __init__(
        self,
        spline_points: list[Vector | tuple[float, ...]],
        width: float = DEFAULT_LINE_WIDTH,
        bias: float = 0.0,
        name: str = "BezierSpline",
        **kwargs,
    ) -> None:
        """Initialise a spline with automatically positioned handles.

        Args:
            spline_points: At least two 2D or 3D anchor positions.
            width: Width of the swept curve profile.
            bias: Lateral profile offset, as a fraction of the width.
            name: The name of the spline object.
            **kwargs: Additional arguments for the Curve base class. The
                ``num_lookup_pts`` argument controls the number of uniformly
                spaced samples in the arc-length lookup table.
        """
        self._spline_params: npt.NDArray[np.float64] | None = None
        self._length_params: npt.NDArray[np.float64] | None = None
        self._cumu_bzr_lens: array | None = None
        self._num_lookup_pts = kwargs.pop("num_lookup_pts", NUM_PARAM_LOOKUP_PTS)
        self._length_geometry = None

        # Create a new curve object
        curve_data = bpy.data.curves.new(name=name, type="CURVE")
        curve_data.dimensions = "2D"
        curve_data.resolution_u = DEFAULT_RESOLUTION

        # Create a Bezier spline and add it to the curve
        assert len(spline_points) > 1, "A spline must contain at least 2 points."
        spline = curve_data.splines.new(type="BEZIER")
        spline.bezier_points.add(count=len(spline_points) - 1)  # contains 1 already

        # Set the bezier points and handle types to 'auto'.
        for i, pt in enumerate(spline_points):
            assert isinstance(pt, Vector | tuple), "Expected a 2D/3D vector."
            bpt = spline.bezier_points[i]
            bpt.co = make_3d_vector(pt)
            bpt.handle_left_type = "AUTO"
            bpt.handle_right_type = "AUTO"

        # Create a new object with the curve data and initialise base class (can only be done at this stage
        # because length must be computable).
        bl_obj = add_object(name, curve_data)
        super().__init__(bl_object=bl_obj, width=width, bias=bias, name=name, **kwargs)

        # Set width and bias
        self.set_width(width)
        self.set_bias(bias)

    def set_width(self, width: float) -> BezierSpline:
        """Set the swept profile width and propagate it to child curves.

        Args:
            width: Profile width in local coordinate units.

        Returns:
            This spline.
        """
        super().set_width(width)

        assert self.object is not None, "The base object has not yet been set."
        profile = self.object.data.bevel_object
        hw = 0.5 * width
        pts = [(-hw, 0), (hw, 0)]  # Centred about the origin

        if profile is not None:
            bpts = profile.data.splines[0].bezier_points
            assert len(bpts) == 2, "Expected a segment as the bevel profile."
            for i, pt in enumerate(pts):
                bpts[i].co = make_3d_vector(pt)
        else:
            line_obj = add_line_segment("profile", *pts)
            self.object.data.bevel_mode = "OBJECT"
            self.object.data.bevel_object = line_obj
            line_obj.parent = self.object

        # Set same width for all children that are curves.
        for c in self.children:
            if isinstance(c, Curve):
                c.set_width(width)

        return self

    def set_bias(self, bias: float) -> BezierSpline:
        """Set the lateral profile offset and update child curves and attachments.

        Args:
            bias: Offset factor, where one unit corresponds to half the width.

        Returns:
            This spline.
        """
        super().set_bias(bias)
        self.object.data.offset = -bias * 0.5 * self._width

        # Set the same bias for all children that are curves.
        for c in self.children:
            if isinstance(c, Curve):
                c.set_bias(bias)

        update_params = (self._update_param_0, self._update_param_1)
        for i, att in enumerate(self._attachments()):
            if att is not None:
                from .joints import Joint

                if isinstance(att, Joint):
                    update_params[i]()

        # If there is an end attachment, update its location and orientation.
        self._update_attachments()

        return self

    def point(self, param: float) -> Vector:
        """Evaluate the spline at an approximate arc-length fraction.

        Args:
            param: Fraction of total arc length in [0, 1].

        Returns:
            Position in the spline's local coordinates.
        """
        bzr_param, bzr_index = self._bezier_curve_info(param)
        p0, h0, h1, p1 = self._control_points(bzr_index)

        t = bzr_param
        _t = 1 - t
        t_sq = t * t
        t_cb = t * t_sq
        _t_sq = _t * _t
        _t_cb = _t * _t_sq

        return _t_cb * p0 + 3 * _t_sq * t * h0 + 3 * _t * t_sq * h1 + t_cb * p1

    def tangent(self, param: float, normalise: bool = False) -> Vector:
        """Evaluate the segment derivative at an approximate arc-length fraction.

        Args:
            param: Fraction of total arc length in [0, 1].
            normalise: Whether to return a unit direction.

        Returns:
            Tangent in local coordinates; if not normalised, its magnitude is
            with respect to the segment's Bezier parameter.
        """
        bzr_param, bzr_index = self._bezier_curve_info(param, is_len_fraction=True)
        tangent = self._bezier_tangent(bzr_index, bzr_param)
        return tangent.normalized() if normalise else tangent

    def normal(self, param: float, normalise: bool = False) -> Vector:
        """Rotate the tangent in the XY plane to obtain a 2D normal.

        Args:
            param: Fraction of total arc length in [0, 1].
            normalise: Whether to normalise the tangent before rotation.

        Returns:
            Normal in local coordinates.

        Raises:
            ValueError: If the spline is not 2D.
        """
        if self.object.data.dimensions != "2D":
            raise ValueError("Normal can currently only be computed for 2D splines.")
        tang = self.tangent(param, normalise)
        return Vector((-tang.y, tang.x, tang.z))

    def length(self, spl_param: float = 1.0) -> float:
        """Integrate arc length from the start to a spline parameter.

        Args:
            spl_param: Spline parameter in [0, 1], distributed equally among
                segments rather than by their lengths.

        Returns:
            Arc length in local coordinate units.
        """
        bzr_param, bzr_index = self._bezier_curve_info(spl_param, is_len_fraction=False)
        arc_len = self._bezier_length(bzr_index, bzr_param)

        cumu_len = self._cumu_bzr_lens[bzr_index]
        assert cumu_len >= 0, "Cumulative length not yet computed."

        return cumu_len + arc_len

    def spline_point(self, pt_index: int) -> bpy.types.BezierSplinePoint:
        """Return the Blender Bezier point at the given anchor index.

        Args:
            pt_index: Anchor index.

        Returns:
            The Blender Bezier point at the given anchor index.
        """
        return self._spline_points()[pt_index]

    # Bezier geometry modifiers ---------------------------------------------------------------------------- #

    def set_left_handle(
        self, point_index: int, location: Vector | Iterable[float], relative: bool = True
    ) -> BezierSpline:
        """Set an anchor's left handle position and switch its type to FREE.

        Args:
            point_index: Anchor index.
            location: Handle position or offset in local coordinates.
            relative: Whether the location is an offset from the anchor.

        Returns:
            This spline.
        """
        self._set_handle("LEFT", point_index, location, relative)
        return self

    def set_right_handle(
        self, point_index: int, location: Vector | Iterable[float], relative: bool = True
    ) -> BezierSpline:
        """Set an anchor's right handle position and switch its type to FREE.

        Args:
            point_index: Anchor index.
            location: Handle position or offset in local coordinates.
            relative: Whether the location is an offset from the anchor.

        Returns:
            This spline.
        """
        self._set_handle("RIGHT", point_index, location, relative)
        return self

    def set_left_handle_type(self, point_index: int, type: str) -> BezierSpline:
        """Set the left handle type and update the spline length.

        Args:
            point_index: Anchor index.
            type: Blender handle type: FREE, ALIGNED, VECTOR or AUTO.

        Returns:
            This spline.
        """
        self._set_handle_type("LEFT", point_index, type)
        return self

    def set_right_handle_type(self, point_index: int, type: str) -> BezierSpline:
        """Set the right handle type and update the spline length.

        Args:
            point_index: Anchor index.
            type: Blender handle type: FREE, ALIGNED, VECTOR or AUTO.

        Returns:
            This spline.
        """
        self._set_handle_type("RIGHT", point_index, type)
        return self

    def set_both_handle_types(self, point_index: int, type: str) -> BezierSpline:
        """Set both handle types at an anchor.

        Args:
            point_index: Anchor index.
            type: Blender handle type: FREE, ALIGNED, VECTOR or AUTO.

        Returns:
            This spline.
        """
        self.set_left_handle_type(point_index, type)
        self.set_right_handle_type(point_index, type)
        return self

    def set_resolution(self, res: int) -> BezierSpline:
        """Set Blender's curve subdivision resolution and return this spline.

        Args:
            res: The subdivision resolution to set.

        Returns:
            This spline.
        """
        self.object.data.resolution_u = res
        return self

    # Property getters/setters ----------------------------------------------------------------------------- #

    @property
    def resolution(self) -> int:
        """Blender's curve subdivision resolution.

        Returns:
            The subdivision resolution.
        """
        return self.object.data.resolution_u

    @resolution.setter
    def resolution(self, res: int) -> None:
        """Set Blender's curve subdivision resolution.

        Args:
            res: The subdivision resolution to set.
        """
        self.set_resolution(res)

    def __deepcopy__(self, memo: dict[int, Any] | None = None) -> BezierSpline:
        """Copy the spline and its Blender bevel profile.

        Args:
            memo: Dictionary tracking objects already copied.

        Returns:
            A deep copy of this spline.
        """
        new_copy = super().__deepcopy__(memo)
        new_bl_obj = new_copy.object
        new_bl_obj.data.bevel_object = deepcopy_object(self.object.data.bevel_object)
        new_bl_obj.data.bevel_object.parent = new_bl_obj
        return new_copy

    # Private methods -------------------------------------------------------------------------------------- #

    def _control_points(self, bzr_index: int) -> tuple[Vector, Vector, Vector, Vector]:
        """Return the two anchors and intervening handles of a segment.

        Args:
            bzr_index: The index of the starting anchor of the segment.

        Returns:
            A tuple containing the positions of the first anchor, its right handle, the second anchor's left handle, and the second anchor.
        """
        bpt0 = self.spline_point(bzr_index)
        bpt1 = self.spline_point(bzr_index + 1)

        p0 = bpt0.co
        h0 = bpt0.handle_right
        h1 = bpt1.handle_left
        p1 = bpt1.co

        return p0, h0, h1, p1

    def _spline_points(self) -> bpy.types.bpy_prop_collection:
        """Return the Blender spline's Bezier point collection.

        Returns:
            The collection of Bezier points for the spline.
        """
        return self.object.data.splines[0].bezier_points

    def _compute_spline_param(self, param: float, is_len_fraction: bool = True) -> float:
        """Convert an arc-length fraction to a spline parameter when requested.

        Args:
            param: The arc-length fraction or spline parameter.
            is_len_fraction: Whether the param is an arc-length fraction.

        Returns:
            The corresponding spline parameter.
        """
        assert 0.0 <= param <= 1.0, f"Parameter must be in range [0, 1]. Got: {param:.3f}"
        # A nondegenerate single curve maps both arc-length endpoints exactly.
        if is_len_fraction and param in (0.0, 1.0) and self._length > 0 and len(self._spline_points()) == 2:
            return param
        return self._get_u_from_s(param * self._length) if is_len_fraction else param

    def _bezier_curve_info(self, param: float, is_len_fraction: bool = True) -> tuple[float, int]:
        """Map a spline parameter or arc-length fraction to a segment and local parameter.

        Args:
            param: The arc-length fraction or spline parameter.
            is_len_fraction: Whether the param is an arc-length fraction.

        Returns:
            A tuple containing the local parameter within the segment and the segment index.
        """
        num_bzr = len(self._spline_points()) - 1
        u = self._compute_spline_param(param, is_len_fraction)
        val = u * num_bzr
        bzr_index = min(math.floor(val), num_bzr - 1)
        bzr_param = val - bzr_index

        return bzr_param, bzr_index

    def _get_handle(self, side: str, point_index: int, relative: bool = True) -> Vector:
        """Return a handle position, optionally relative to its anchor.

        Args:
            side: "LEFT" or "RIGHT" indicating which handle to return.
            point_index: The index of the anchor point.
            relative: Whether to return the handle position relative to the anchor.

        Returns:
            The handle position as a Vector.
        """
        assert side in ["LEFT", "RIGHT"]
        pt = self.spline_point(point_index)
        handle_str = "handle_" + side.lower()
        loc = getattr(pt, handle_str)
        return loc - pt.co if relative else loc

    def _set_handle(
        self, side: str, point_index: int, location: Vector | Iterable[float], relative: bool = True
    ) -> None:
        """Set a free handle and refresh cached length information.

        Args:
            side: "LEFT" or "RIGHT" indicating which handle to set.
            point_index: The index of the anchor point.
            location: The new handle location.
            relative: Whether the location is relative to the anchor.
        """
        loc = make_3d_vector(location)
        pt = self.spline_point(point_index)
        assert side in ["LEFT", "RIGHT"]
        handle_str = "handle_" + side.lower()
        try:
            self._set_handle_type(side, point_index, "FREE", update_length=False)
            setattr(pt, handle_str, pt.co + loc if relative else loc)
        finally:
            self._update_length()

    def _set_handle_type(self, side: str, point_index: int, type: str, update_length: bool = True) -> None:
        """Set a handle type, optionally deferring the length update.

        Args:
            side: "LEFT" or "RIGHT" indicating which handle to set.
            point_index: The index of the anchor point.
            type: The handle type ("FREE", "ALIGNED", "VECTOR", "AUTO").
            update_length: Whether to update the cached length after setting the type.
        """
        pt = self.spline_point(point_index)
        assert side in ["LEFT", "RIGHT"]
        assert type.upper() in ["FREE", "ALIGNED", "VECTOR", "AUTO"]
        handle_type_str = "handle_" + side.lower() + "_type"
        setattr(pt, handle_type_str, type.upper())

        # Length possibly changed, so update stored value.
        if update_length:
            self._update_length()

    def _set_param(self, param: float, end_idx: int) -> None:
        """Set an endpoint's arc-length fraction and corresponding bevel factor.

        Args:
            param: The arc-length fraction to set.
            end_idx: The index of the endpoint (0 for start, 1 for end).
        """
        super()._set_param(param, end_idx)

        # Compute attachment offset and terminate curve accordingly.
        if end_idx == 0:
            param_offs = self._compute_offset_param_0(param)
            bf = self._compute_spline_param(param_offs)
            self.object.data.bevel_factor_start = bf
        else:
            param_offs = self._compute_offset_param_1(param)
            bf = self._compute_spline_param(param_offs)
            self.object.data.bevel_factor_end = bf

    def _update_attachment(self, end_idx: int) -> None:
        """Update an endcap's position and orientation at the specified endpoint.

        Args:
            end_idx: The index of the endpoint (0 for start, 1 for end).
        """
        if end_idx == 0:
            param = self._param_0
            attmt = self._attachment_0
            param_offs = self._compute_offset_param_0(param)
        else:
            param = self.param_1
            attmt = self._attachment_1
            param_offs = self._compute_offset_param_1(param)

        if attmt is None:
            return

        if isinstance(attmt, Endcap):
            # Set location
            pt = self.point(param)
            nm = self.normal(param_offs, normalise=True)
            bias_offs = -self._bias * 0.5 * self._width * nm
            attmt.location = pt + bias_offs
            attmt.layer = self.layer + 1  # appear above the curve

            # Set orientation
            pt_offs = self.point(param_offs)
            y_dir = pt - pt_offs
            sgn = 1 if end_idx == 1 else -1
            if math.isclose(param, param_offs, rel_tol=1e-4):
                y_dir = sgn * self.tangent(param_offs)

            if self._dimension() == 2:
                x_dir = rotate_90(y_dir, clockwise=True)
            else:
                x_dir = -sgn * self.normal(param_offs)

            attmt.set_orientation(x_dir, y_dir)

    def _derivative_coefficients(self, bzr_index: int) -> tuple[Coefficients, Coefficients, Coefficients]:
        """Return a segment's derivative as polynomial coefficients in its local parameter.

        The derivative with respect to the local parameter t is ``a + b * t + c * t ** 2``.
        Control points are read from Blender once per call and combined in double precision
        (``mathutils.Vector`` is single precision).

        Args:
            bzr_index: The index of the Bezier segment.

        Returns:
            The component tuples of the vector coefficients a, b and c.
        """
        p0, h0, h1, p1 = (tuple(p) for p in self._control_points(bzr_index))
        a = tuple(3 * (h0[i] - p0[i]) for i in range(3))
        b = tuple(6 * (p0[i] - 2 * h0[i] + h1[i]) for i in range(3))
        c = tuple(3 * (-p0[i] + 3 * h0[i] - 3 * h1[i] + p1[i]) for i in range(3))
        return a, b, c

    def _bezier_tangent(self, bzr_index: int, param: float) -> Vector:
        """Evaluate a segment's derivative with respect to its local parameter.

        Args:
            bzr_index: The index of the Bezier segment.
            param: The local parameter within the segment.

        Returns:
            The derivative as a Vector.
        """
        a, b, c = self._derivative_coefficients(bzr_index)
        return Vector(a[i] + param * (b[i] + param * c[i]) for i in range(3))

    def _bezier_length(self, bzr_index: int, param: float = 1.0) -> float:
        """Integrate a segment's speed from zero to its local parameter.

        Args:
            bzr_index: The index of the Bezier segment.
            param: The local parameter within the segment (default is 1.0).

        Returns:
            The arc length as a float.
        """
        a, b, c = self._derivative_coefficients(bzr_index)

        def integrand(t: float) -> float:
            return math.sqrt(sum((a[i] + t * (b[i] + t * c[i])) ** 2 for i in range(3)))

        disable_print()  # Disable output regarding round-off errors
        try:
            # Floor the tolerance so that near-zero-length curves don't demand accuracy below round-off.
            eps = max(RELATIVE_LENGTH_ERR * self._length, MIN_ABSOLUTE_LENGTH_ERR)
            arc_len, err = integrate.quad(integrand, 0.0, param, epsabs=eps)
        finally:
            enable_print()

        assert err < eps, "Arc length computation failed."
        return arc_len

    def _map_u_to_s(self) -> None:
        """Build sampled spline-parameter and cumulative-length lookup arrays.

        This method samples the spline at uniformly distributed points and at the intermediate
        Bezier points to create lookup tables for spline parameters and their corresponding
        cumulative arc lengths. Partial segment lengths are computed for all samples at once with
        fixed-order Gauss-Legendre quadrature. The resulting arrays are stored in self._spline_params
        and self._length_params.
        """
        num_pts = self._num_lookup_pts
        num_bzr_crvs = len(self._spline_points()) - 1

        # Uniform samples plus the interior anchors, so that segment boundaries are represented exactly.
        uniform = np.minimum(np.arange(num_pts) / (num_pts - 1), 1.0)
        anchors = np.arange(1, num_bzr_crvs) / num_bzr_crvs
        u = np.sort(np.concatenate((uniform, anchors)))

        scaled = u * num_bzr_crvs
        seg = np.minimum(np.floor(scaled).astype(int), num_bzr_crvs - 1)
        local = scaled - seg

        # Per-segment derivative polynomial coefficients, read from Blender once per segment.
        coeffs = np.array([self._derivative_coefficients(i) for i in range(num_bzr_crvs)])

        # Gauss-Legendre quadrature of the speed over [0, local] for every sample at once.
        nodes, weights = _GAUSS_LEGENDRE
        t = 0.5 * local[:, None] * (nodes[None, :] + 1.0)  # (samples, nodes)
        c = coeffs[seg]  # (samples, 3, 3)
        deriv = c[:, None, 0, :] + t[:, :, None] * (c[:, None, 1, :] + t[:, :, None] * c[:, None, 2, :])
        speed = np.sqrt(np.sum(deriv * deriv, axis=2))
        partial = 0.5 * local * (speed @ weights)

        cumu = np.asarray(self._cumu_bzr_lens, dtype=float)
        self._spline_params = u
        self._length_params = cumu[seg] + partial

    def _get_u_from_s(self, s: float) -> float:
        """Interpolate a spline parameter for an arc length, building the table if needed.

        Args:
            s: The arc length for which to find the corresponding spline parameter.

        Returns:
            The interpolated spline parameter as a float.

        Raises:
            Exception: If the arc length is out of bounds.
        """
        if not (0 <= s <= self._length):
            raise Exception("The length parameter is out of bounds.")
        if self._length_params is None:
            self._map_u_to_s()
        return float(np.interp(s, self._length_params, self._spline_params))

    def _dimension(self) -> int:
        """Return the dimensionality of the Blender curve data.

        Returns:
            The dimensionality as an integer.
        """
        return int(self.object.data.dimensions[0])

    def _update_length(self) -> None:
        """Refresh cached lengths after geometry changes and invalidate the lookup table."""
        points = self._spline_points()
        # A parent chain can request an update after direct Blender-side edits.
        geometry = tuple((tuple(p.co), tuple(p.handle_left), tuple(p.handle_right)) for p in points)
        if geometry == self._length_geometry:
            return

        self._length_geometry = None
        self._spline_params = None
        self._length_params = None
        n_bezier = len(points) - 1
        self._cumu_bzr_lens = array("f", [-1] * n_bezier)
        cumu_lens = self._cumu_bzr_lens

        cumu_lens[0] = 0
        for i in range(1, n_bezier):
            cumu_lens[i] = cumu_lens[i - 1] + self._bezier_length(i - 1)

        super()._update_length()
        self._length_geometry = geometry
