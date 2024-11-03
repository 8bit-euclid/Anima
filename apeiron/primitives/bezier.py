import bpy
from apeiron.globals.general import Vector, get_3d_vector, add_object, add_line_segment
from .curve import BaseCurve, DEFAULT_LINE_WIDTH


class BezierSpline(BaseCurve):
    def __init__(self, points, name='BezierSpline', width=DEFAULT_LINE_WIDTH, bias=0.0):
        assert len(points) > 1, 'A Bezier spline must contain at least 2 points.'

        # Create a new curve object
        curve_data = bpy.data.curves.new(name=name, type='CURVE')
        curve_data.dimensions = '3D'
        curve_data.resolution_u = 10

        # Create a Bezier spline and add it to the curve
        spline = curve_data.splines.new(type='BEZIER')
        spline.bezier_points.add(count=len(points)-1)

        # Set the bezier points and handle types to 'auto'.
        for i, pt in enumerate(points):
            bpt = spline.bezier_points[i]
            bpt.co = get_3d_vector(pt)
            bpt.handle_left_type = 'AUTO'
            bpt.handle_right_type = 'AUTO'

        # Create a new object with the curve data.
        bl_obj = add_object(name, curve_data)
        super().__init__(name, bl_obj, width, bias)

    def point(self, t: float) -> Vector:
        pass

    def tangent(self, t: float, normalise=False) -> Vector:
        pass

    def normal(self, t: float, normalise=False) -> Vector:
        pass

    def length(self, t: float) -> float:
        pass

    def get_point(self, index: int):
        spline = self.bl_obj.data.splines[0]
        pts = spline.bezier_points
        assert index < len(pts), 'Bezier point index is out of bounds.'
        return pts[index]

    def set_resolution(self, res: int):
        self.bl_obj.data.resolution_u = res

    def set_left_handle(self, point_index: int, location, relative=True):
        self._set_handle('LEFT', point_index, location, relative)

    def set_right_handle(self, point_index: int, location, relative=True):
        self._set_handle('RIGHT', point_index, location, relative)

    def set_left_handle_type(self, point_index: int, type: str):
        self._set_handle_type('LEFT', point_index, type)

    def set_right_handle_type(self, point_index: int, type: str):
        self._set_handle_type('RIGHT', point_index, type)

    # Private methods
    def _set_handle(self, side: str, point_index: int, location, relative=True):
        loc = get_3d_vector(location)
        pt = self.get_point(point_index)
        assert side in ['LEFT', 'RIGHT']
        handle_str = 'handle_' + side.lower()
        setattr(pt, handle_str, pt.co + loc if relative else loc)

    def _set_handle_type(self, side: str, point_index: int, type: str):
        pt = self.get_point(point_index)
        assert side in ['LEFT', 'RIGHT']
        assert type in ['FREE', 'ALIGNED', 'VECTOR', 'AUTO']
        handle_type_str = 'handle_' + side.lower() + '_type'
        setattr(pt, handle_type_str, type)


class BezierCurve(BezierSpline):
    def __init__(self, point0, point1, name='BezierCurve', width=DEFAULT_LINE_WIDTH, bias=0.0):
        super().__init__([point0, point1], name, width, bias)

    def set_handle_0(self, location, relative=True):
        self._set_handle_type('RIGHT', 0, 'FREE')
        self._set_handle('RIGHT', 0, location, relative)

    def set_handle_1(self, location, relative=True):
        self._set_handle_type('LEFT', 1, 'FREE')
        self._set_handle('LEFT', 1, location, relative)
