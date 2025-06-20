import math
import numpy as np
import bpy
from typing import Any, Optional
from array import array
from scipy import integrate
from anima.globals.general import (SMALL_OFFSET, Vector, add_line_segment,
                                   add_object, deepcopy_object, disable_print, enable_print,
                                   get_3d_vector, rotate_90)
from .curves import DEFAULT_LINE_WIDTH, Curve
from .endcaps import Endcap

DEFAULT_RESOLUTION = 100
RELATIVE_LENGTH_ERR = 1.0e-3  # 0.1% of the length
NUM_PARAM_LOOKUP_PTS = 40


class BezierSpline(Curve):
    def __init__(self, spline_points: list[Vector | tuple], width: float = DEFAULT_LINE_WIDTH,
                 bias: float = 0.0, name: str = 'BezierSpline', **kwargs):
        self._spl_params: 'np.ndarray'[float] = None
        self._len_params: 'np.ndarray'[float] = None
        self._cumu_bzr_lengths: array[float] = None
        num_pts_key = 'num_lookup_pts'
        if num_pts_key in kwargs:
            self._num_lookup_pts = kwargs[num_pts_key]
            del kwargs[num_pts_key]  # Remove so it is not passed on
        else:
            self._num_lookup_pts = NUM_PARAM_LOOKUP_PTS

        # Create a new curve object
        curve_data = bpy.data.curves.new(name=name, type='CURVE')
        curve_data.dimensions = '2D'
        curve_data.resolution_u = DEFAULT_RESOLUTION

        # Create a Bezier spline and add it to the curve
        assert len(spline_points) > 1, 'A spline must contain at least 2 points.'
        spline = curve_data.splines.new(type='BEZIER')
        spline.bezier_points.add(
            count=len(spline_points)-1)  # contains 1 already

        # Set the bezier points and handle types to 'auto'.
        for i, pt in enumerate(spline_points):
            bpt = spline.bezier_points[i]
            bpt.co = get_3d_vector(pt)
            bpt.handle_left_type = 'AUTO'
            bpt.handle_right_type = 'AUTO'

        # Create a new object with the curve data and initialise base class (can only be done at this stage
        # because length must be computable).
        bl_obj = add_object(name, curve_data)
        super().__init__(bl_object=bl_obj, width=width, bias=bias, name=name, **kwargs)

        # Set width and bias
        self.set_width(width)
        self.set_bias(bias)

    def set_width(self, width):
        super().set_width(width)

        assert self.bl_obj is not None, 'The base object has not yet been set.'
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

        return self

    def set_bias(self, bias: float):
        super().set_bias(bias)
        self.bl_obj.data.offset = -bias * 0.5 * self._width

        # Set the same bias for all children
        for c in self.children:
            c.set_bias(bias)

        update_params = [self._update_param_0, self._update_param_1]
        for i, att in enumerate(self._attachments()):
            if att is not None:
                from .joints import Joint
                if isinstance(att, Joint):
                    update_params[i]()

        # If there is an end attachment, update its location and orientation.
        self._update_attachments()

        return self

    def point(self, param: float) -> Vector:
        bzr_param, bzr_index = self._bezier_curve_info(param)
        p0, h0, h1, p1 = self._control_points(bzr_index)

        t = bzr_param
        _t = (1 - t)
        t_sq = t * t
        t_cb = t * t_sq
        _t_sq = _t * _t
        _t_cb = _t * _t_sq

        return _t_cb * p0 + 3 * _t_sq * t * h0 + 3 * _t * t_sq * h1 + t_cb * p1

    def tangent(self, param: float, normalise=False) -> Vector:
        bzr_param, bzr_index = \
            self._bezier_curve_info(param, is_len_fraction=True)
        tangent = self._bezier_tangent(bzr_index, bzr_param)
        return tangent.normalized() if normalise else tangent

    def normal(self, param: float, normalise=False) -> Vector:
        assert self.object.data.dimensions == '2D'
        tang = self.tangent(param, normalise)
        return Vector((-tang.y, tang.x, tang.z))

    def length(self, spl_param: float = 1.0) -> float:
        bzr_param, bzr_index = \
            self._bezier_curve_info(spl_param, is_len_fraction=False)
        arc_len = self._bezier_length(bzr_index, bzr_param)

        cumu_len = self._cumu_bzr_lengths[bzr_index]
        assert cumu_len >= 0, 'Cumulative length not yet computed.'

        return cumu_len + arc_len

    def spline_point(self, pt_index: int):
        return self._spline_points()[pt_index]

    # Bezier geometry modifiers ---------------------------------------------------------------------------- #

    def set_left_handle(self, point_index: int, location, relative: bool = True):
        self.set_left_handle_type(point_index, 'FREE')
        self._set_handle('LEFT', point_index, location, relative)

    def set_right_handle(self, point_index: int, location, relative: bool = True):
        self.set_right_handle_type(point_index, 'FREE')
        self._set_handle('RIGHT', point_index, location, relative)

    def set_left_handle_type(self, point_index: int, type: str):
        self._set_handle_type('LEFT', point_index, type)

    def set_right_handle_type(self, point_index: int, type: str):
        self._set_handle_type('RIGHT', point_index, type)

    def set_both_handle_types(self, point_index: int, type: str):
        self.set_left_handle_type(point_index, type)
        self.set_right_handle_type(point_index, type)

    def set_resolution(self, res: int):
        self.bl_obj.data.resolution_u = res

    # Property getters/setters ----------------------------------------------------------------------------- #

    @property
    def resolution(self) -> int:
        """Get the curve's resolution (number of sub-division intervals)."""
        return self.bl_obj.data.resolution_u

    @resolution.setter
    def resolution(self, res: int):
        """Set the curve's resolution."""
        self.set_resolution(res)

    def __deepcopy__(self, memo: Optional[dict[int, Any]] = None):
        new_copy = super().__deepcopy__(memo)
        new_bl_obj = new_copy.bl_obj
        new_bl_obj.data.bevel_object = \
            deepcopy_object(self.bl_obj.data.bevel_object)
        new_bl_obj.data.bevel_object.parent = new_bl_obj
        return new_copy

    # Private methods -------------------------------------------------------------------------------------- #

    def _control_points(self, bzr_index: int):
        bpt0 = self.spline_point(bzr_index)
        bpt1 = self.spline_point(bzr_index + 1)

        p0 = bpt0.co
        h0 = bpt0.handle_right
        h1 = bpt1.handle_left
        p1 = bpt1.co

        return p0, h0, h1, p1

    def _spline_points(self):
        return self.bl_obj.data.splines[0].bezier_points

    def _compute_spline_param(self, param: float, is_len_fraction: bool = True) -> float:
        assert 0.0 <= param <= 1.0, f'Parameter must be in range [0, 1]. Got: {param:.3f}'
        return self._get_u_from_s(param * self._length) if is_len_fraction else param

    def _bezier_curve_info(self, param: float, is_len_fraction: bool = True) -> tuple[float, int]:
        num_bzr = len(self._spline_points()) - 1
        u = self._compute_spline_param(param, is_len_fraction)
        val = u * num_bzr
        bzr_index = min(math.floor(val), num_bzr - 1)
        bzr_param = val - bzr_index

        return bzr_param, bzr_index

    def _get_handle(self, side: str, point_index: int, relative: bool = True) -> Vector:
        assert side in ['LEFT', 'RIGHT']
        pt = self.spline_point(point_index)
        handle_str = 'handle_' + side.lower()
        loc = getattr(pt, handle_str)
        return loc - pt.co if relative else loc

    def _set_handle(self, side: str, point_index: int, location, relative: bool = True):
        loc = get_3d_vector(location)
        pt = self.spline_point(point_index)
        assert side in ['LEFT', 'RIGHT']
        handle_str = 'handle_' + side.lower()
        setattr(pt, handle_str, pt.co + loc if relative else loc)

        # Length possibly changed, so update stored value.
        self._update_length()

    def _set_handle_type(self, side: str, point_index: int, type: str):
        pt = self.spline_point(point_index)
        assert side in ['LEFT', 'RIGHT']
        assert type.upper() in ['FREE', 'ALIGNED', 'VECTOR', 'AUTO']
        handle_type_str = 'handle_' + side.lower() + '_type'
        setattr(pt, handle_type_str, type.upper())

        # Length possibly changed, so update stored value.
        self._update_length()

    def _set_param(self, param: float, end_idx: int):
        super()._set_param(param, end_idx)

        # Compute attachment offset and terminate curve accordingly.
        if end_idx == 0:
            param_offs = self._compute_offset_param_0(param)
            bf = self._compute_spline_param(param_offs)
            self.bl_obj.data.bevel_factor_start = bf
        else:
            param_offs = self._compute_offset_param_1(param)
            bf = self._compute_spline_param(param_offs)
            self.bl_obj.data.bevel_factor_end = bf

    def _update_attachment(self, end_idx: int):
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
            pt.z += SMALL_OFFSET
            nm = self.normal(param_offs, normalise=True)
            bias_offs = -self._bias * 0.5 * self._width * nm
            attmt.location = pt + bias_offs

            # Set orientation
            pt_offs = self.point(param_offs)
            pt_offs.z += SMALL_OFFSET  # appear above the curve
            y_dir = pt - pt_offs
            sgn = 1 if end_idx == 1 else -1
            if math.isclose(param, param_offs, rel_tol=1e-4):
                y_dir = sgn * self.tangent(param_offs)

            if self._dimension() == 2:
                x_dir = rotate_90(y_dir, clockwise=True)
            else:
                x_dir = -sgn * self.normal(param_offs)

            attmt.set_orientation(x_dir, y_dir)

    def _bezier_tangent(self, bzr_index: int, param: float) -> Vector:
        p0, h0, h1, p1 = self._control_points(bzr_index)
        t = param
        t_sq = t * t
        return -3 * (1 - t)**2 * p0 + 3 * (1 - 4*t + 3*t_sq) * h0 + \
            3 * (2*t - 3*t_sq) * h1 + 3 * t_sq * p1

    def _bezier_length(self, bzr_index: int, param: float = 1.0) -> float:
        def integrand(t):
            return self._bezier_tangent(bzr_index, t).magnitude

        disable_print()  # Disable output regarding round-off errors
        l = self._length
        eps = RELATIVE_LENGTH_ERR * l if l > 0 else 1e-5
        arc_len, err = integrate.quad(integrand, 0.0, param, epsabs=eps)
        enable_print()

        assert err < eps, 'Arc length computation failed.'
        return arc_len

    def _map_u_to_s(self):
        num_pts = self._num_lookup_pts
        spl_params = [-1.0]*num_pts
        len_params = [-1.0]*num_pts

        # Compute the lengths at uniformly distributed points.
        du = 1.0 / (num_pts - 1)
        for i in range(num_pts):
            u = min(i*du, 1)
            spl_params[i] = u
            len_params[i] = self.length(u)

        # Compute the extra parameters at spline points.
        n_bzr_crv = len(self._spline_points()) - 1
        num_bzr_pts = n_bzr_crv - 1  # Only the intermediate points are inserted
        extra_spl_params = [-1.0]*num_bzr_pts
        extra_len_params = [-1.0]*num_bzr_pts
        du = 1 / n_bzr_crv
        for i in range(num_bzr_pts):
            u = (i + 1) * du
            extra_spl_params[i] = u
            extra_len_params[i] = self.length(u)
        spl_params.extend(extra_spl_params)
        len_params.extend(extra_len_params)

        # Zip the lists together, sort based on first list, and unzip and then convert back to lists.
        sorted_lists = zip(*sorted(zip(spl_params, len_params)))
        spl_params, len_params = map(list, sorted_lists)

        # Lastly, convert to numpy arrays.
        self._spl_params = np.array(spl_params, dtype=float)
        self._len_params = np.array(len_params, dtype=float)

    def _get_u_from_s(self, s):
        if not (0 <= s <= self._length):
            raise Exception('The length parameter is out of bounds.')
        return float(np.interp(s, self._len_params, self._spl_params))

    def _dimension(self) -> int:
        return int(self.bl_obj.data.dimensions[0])

    def _update_length(self):
        n_bezier = len(self._spline_points()) - 1
        self._cumu_bzr_lengths = array('f', [-1]*n_bezier)
        cumu_lens = self._cumu_bzr_lengths

        cumu_lens[0] = 0
        for i in range(1, n_bezier):
            cumu_lens[i] = cumu_lens[i - 1] + self._bezier_length(i - 1)

        self._map_u_to_s()

        super()._update_length()


class BezierCurve(BezierSpline):
    def __init__(self, point_0: Vector | tuple, point_1: Vector | tuple, width: float = DEFAULT_LINE_WIDTH,
                 bias: float = 0.0, name: str = 'BezierCurve', **kwargs):
        super().__init__(spline_points=[point_0, point_1],
                         width=width, bias=bias, name=name, **kwargs)

    def set_handle_0(self, location, relative=True):
        """Set the handle position at point 0."""
        self.set_right_handle(0, location, relative)
        return self

    def set_handle_1(self, location, relative=True):
        """Set the handle position at point 1."""
        self.set_left_handle(1, location, relative)
        return self

    # Property getters/setters ----------------------------------------------------------------------------- #

    @property
    def handle_0(self) -> Vector:
        """Get the curve's handle 0."""
        return self._get_handle(side='RIGHT', point_index=0, relative=True)

    @handle_0.setter
    def handle_0(self, direction: Vector | tuple):
        """Set the curve's handle 0."""
        self.set_handle_0(direction)

    @property
    def handle_1(self) -> Vector:
        """Get the curve's handle 1"""
        return self._get_handle(side='LEFT', point_index=1, relative=True)

    @handle_1.setter
    def handle_1(self, direction: Vector | tuple):
        """Set the curve's handle 1."""
        self.set_handle_1(direction)
