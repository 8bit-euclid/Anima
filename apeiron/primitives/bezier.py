import bpy
import math
import bisect
from apeiron.globals.general import Vector, get_3d_vector, add_object, disable_print, \
    enable_print, add_line_segment, SMALL_OFFSET
from .curves import BaseCurve, DEFAULT_LINE_WIDTH
from scipy import integrate
import numpy as np

DEFAULT_DASH_LENGTH = 0.1
DEFAULT_GAP_LENGTH = 0.02


class BezierSpline(BaseCurve):
    def __init__(self, spline_points, name='BezierSpline', width=DEFAULT_LINE_WIDTH, bias=0.0):
        assert len(spline_points) > 1, 'A spline must contain at least 2 points.'

        # Create a new curve object
        curve_data = bpy.data.curves.new(name=name, type='CURVE')
        curve_data.dimensions = '2D'
        curve_data.resolution_u = 10

        # Create a Bezier spline and add it to the curve
        spline = curve_data.splines.new(type='BEZIER')
        spline.bezier_points.add(
            count=len(spline_points)-1)  # contains 1 already

        # Set the bezier points and handle types to 'auto'.
        for i, pt in enumerate(spline_points):
            bpt = spline.bezier_points[i]
            bpt.co = get_3d_vector(pt)
            bpt.handle_left_type = 'AUTO'
            bpt.handle_right_type = 'AUTO'

        # Create a new object with the curve data.
        bl_obj = add_object(name, curve_data)
        super().__init__(bl_obj, name, width, bias)

        # Map spline parameter to length parameter.
        self.mapped_lengths = False
        self.length_fraction = None

    def set_width(self, width):
        assert self.bl_obj is not None, 'The base object has not yet been set.'
        self.width = width

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
            # self.bl_obj.data.bevel_factor_end = 0.5
            line_obj.parent = self.bl_obj

        # Set same width for all children
        for c in self.children:
            c.set_width(width)

        return self

    def set_bias(self, bias: float):
        assert -1.0 <= bias <= 1.0, 'The bias must be in the range [-1, 1].'
        self.bl_obj.data.offset = -bias * (0.5 * self.width)

        # Set the same bias for all children
        for c in self.children:
            c.set_bias(bias)

        return self

    def set_start_param(self, param, is_len_factor: bool = True):
        self._set_param(param, 0, is_len_factor)

    def set_end_param(self, param, is_len_factor: bool = True):
        self._set_param(param, 1, is_len_factor)

    def make_dashed(self, dash_len: float = DEFAULT_DASH_LENGTH, gap_len: float = DEFAULT_GAP_LENGTH,
                    offset: float = 0.0):
        # Compute u intervals corresponding to the dashes.
        total_len = self.length()
        delta_u = dash_len + gap_len

        u0 = delta_u % offset
        while u0 < total_len:
            # Compute u1 and make a dash over interval (u0, u1)
            u1 = min(u0 + dash_len, total_len)
            # todo

            # Jump to next dash
            u0 += delta_u

    def point(self, param: float, is_len_factor: bool = True) -> Vector:
        bzr_param, bzr_index = self._compute_bezier_param(param, is_len_factor)
        p0, h0, h1, p1 = self._get_control_points(bzr_index)

        t = bzr_param
        return (1 - t)**3 * p0 + 3 * (1 - t)**2 * t * h0 + 3 * (1 - t) * t**2 * h1 + t**3 * p1

    def tangent(self, param: float, normalise=False, is_len_factor: bool = True) -> Vector:
        bzr_param, bzr_index = self._compute_bezier_param(param, is_len_factor)
        p0, h0, h1, p1 = self._get_control_points(bzr_index)

        t = bzr_param
        tang = -3 * (1 - t)**2 * p0 + 3 * (1 - 4*t + 3*t**2) * \
            h0 + 3 * (2*t - 3*t**2) * h1 + 3 * t**2 * p1
        return tang.normalized() if normalise else tang

    def normal(self, param: float, normalise=False, is_len_factor: bool = True) -> Vector:
        assert self.object.data.dimensions == '2D'
        tang = self.tangent(param, normalise, is_len_factor)
        return Vector((-tang.y, tang.x, tang.z))

    def length(self, spl_param: float = 1.0) -> float:
        n_bezier = len(self._get_spline_points()) - 1

        def integrand(u):
            return self.tangent(u, is_len_factor=False).magnitude

        n_segs = max(1, int(10*spl_param))
        du = spl_param / n_segs
        tot_len = 0
        for i in range(n_segs):
            u0 = du * i
            u1 = du * (i + 1)

            disable_print()  # Disable output regarding round-off errors
            seg_len, err = integrate.quad(integrand, u0, u1)
            enable_print()

            assert abs(err) < 1e-6, 'Arc length computation failed'
            tot_len += n_bezier * seg_len

        return tot_len

    def set_resolution(self, res: int):
        self.bl_obj.data.resolution_u = res

    def set_left_handle(self, point_index: int, location, relative=True):
        self.set_left_handle_type(point_index, 'FREE')
        self._set_handle('LEFT', point_index, location, relative)

    def set_right_handle(self, point_index: int, location, relative=True):
        self.set_right_handle_type(point_index, 'FREE')
        self._set_handle('RIGHT', point_index, location, relative)

    def set_left_handle_type(self, point_index: int, type: str):
        self._set_handle_type('LEFT', point_index, type)

    def set_right_handle_type(self, point_index: int, type: str):
        self._set_handle_type('RIGHT', point_index, type)

    def spline_point(self, pt_index: int):
        pts = self._get_spline_points()
        assert 0 <= pt_index < len(pts), 'Spline point index is out of bounds.'
        return pts[pt_index]

    # Private methods
    def _get_control_points(self, bzr_index: int):
        bpt0 = self.spline_point(bzr_index)
        bpt1 = self.spline_point(bzr_index + 1)

        p0 = bpt0.co
        h0 = bpt0.handle_right
        h1 = bpt1.handle_left
        p1 = bpt1.co

        return p0, h0, h1, p1

    def _get_spline_points(self):
        return self.bl_obj.data.splines[0].bezier_points

    def _compute_spline_param(self, param: float, is_len_factor: bool = True) -> float:
        assert 0.0 <= param <= 1.0, "Parameter must be in range [0, 1]"
        if is_len_factor and not self.mapped_lengths:
            self._build_param_mapping()
        return self._get_u_from_s(param * self['s'][-1]) if is_len_factor else param

    def _compute_bezier_param(self, param: float, is_len_factor: bool = True) -> float:
        u = self._compute_spline_param(param, is_len_factor)

        num_bzr = len(self._get_spline_points()) - 1
        bzr_intvl = 1.0 / num_bzr

        bzr_index = math.floor(u / bzr_intvl)
        if u % bzr_intvl == 0 and u > 0:
            bzr_index -= 1
        bzr_param = (u - bzr_index * bzr_intvl) / bzr_intvl

        return bzr_param, bzr_index

    def _set_handle(self, side: str, point_index: int, location, relative=True):
        loc = get_3d_vector(location)
        pt = self.spline_point(point_index)
        assert side in ['LEFT', 'RIGHT']
        handle_str = 'handle_' + side.lower()
        setattr(pt, handle_str, pt.co + loc if relative else loc)

    def _set_handle_type(self, side: str, point_index: int, type: str):
        pt = self.spline_point(point_index)
        assert side in ['LEFT', 'RIGHT']
        assert type in ['FREE', 'ALIGNED', 'VECTOR', 'AUTO']
        handle_type_str = 'handle_' + side.lower() + '_type'
        setattr(pt, handle_type_str, type)

    def _set_param(self, param, end_index: int, is_len_factor: bool = True):
        if end_index == 0:
            param_offs = min(param + self.offset_0, 1.0)
            u = self._compute_spline_param(param_offs, is_len_factor)
            self.bl_obj.data.bevel_factor_start = u
            attmt = self.attachment_0
        else:
            param_offs = max(param - self.offset_1, 0.0)
            u = self._compute_spline_param(param_offs, is_len_factor)
            self.bl_obj.data.bevel_factor_end = u
            attmt = self.attachment_1

        # If there is an end attachment, update its location and orientation
        if attmt is not None:
            # location
            pt = self.point(param, is_len_factor)
            pt.z += SMALL_OFFSET
            attmt.location = pt

            # orientation
            y_dir = self.tangent(param, is_len_factor=is_len_factor)
            if self._dimension() == 2:
                x_dir = Vector((y_dir.y, -y_dir.x, 0))
            else:
                x_dir = -self.normal(param, is_len_factor=is_len_factor)

            # Rotate by 180 degrees if start of the curve
            if end_index == 0:
                x_dir *= -1.0
                y_dir *= -1.0

            attmt.set_orientation(x_dir, y_dir)

    def _build_param_mapping(self, num_pts: int = 101):
        self['u'] = [-1.0] * num_pts
        self['s'] = [-1.0] * num_pts
        du = 1.0 / (num_pts - 1)

        for i in range(num_pts):
            self['u'][i] = i * du
            self['s'][i] = self.length(self['u'][i])

        # Todo - add bezier boundary points too (discontinuous).

        self.mapped_lengths = True
        self.length_fraction = 1.0 / self['s'][-1]

    def _get_u_from_s(self, s):
        if not self.mapped_lengths:
            self._build_param_mapping()

        s_list = self['s']
        u_list = self['u']

        if s < s_list[0] or s > s_list[-1]:
            raise Exception('The length parameter is out of bounds.')

        # Find bounding interval and linearly interpolate
        idx = bisect.bisect_left(s_list, s)

        if idx == 0:
            return u_list[0]
        elif idx == len(s_list):
            return u_list[-1]

        s0 = s_list[idx - 1]
        s1 = s_list[idx]
        u0 = u_list[idx - 1]
        u1 = u_list[idx]

        return u0 + (u1 - u0) * (s - s0) / (s1 - s0)

    def _dimension(self):
        return int(self.bl_obj.data.dimensions[0])


class BezierCurve(BezierSpline):
    def __init__(self, point_0, point_1, name='BezierCurve', width=DEFAULT_LINE_WIDTH, bias=0.0):
        super().__init__([point_0, point_1], name, width, bias)

    def set_handle_0(self, location, relative=True):
        """Set the handle position at point 0."""
        self.set_right_handle(0, location, relative)
        return self

    def set_handle_1(self, location, relative=True):
        """Set the handle position at point 1."""
        self.set_left_handle(1, location, relative)
        return self
