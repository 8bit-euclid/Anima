from anima.globals.general import get_3d_vector
from .curves import DEFAULT_LINE_WIDTH
from .bezier import BezierCurve


class Segment(BezierCurve):
    def __init__(self, point_0, point_1, width=DEFAULT_LINE_WIDTH, bias=0.0, name='Segment', **kwargs):
        super().__init__(point_0, point_1, width=width, bias=bias, name=name, **kwargs)


# Disable redundant methods in Segment class.
Segment.set_handle_0 = None
Segment.set_handle_1 = None


class Ray(Segment):
    def __init__(self, point, direction, width=DEFAULT_LINE_WIDTH, bias=0.0, name='Ray', **kwargs):
        pt_0 = get_3d_vector(point)
        pt_1 = pt_0 + 100.0 * get_3d_vector(direction)
        super().__init__(pt_0, pt_1, width=width, bias=bias, name=name, **kwargs)


class Line(Segment):
    def __init__(self, point, direction, width=DEFAULT_LINE_WIDTH, bias=0.0, name='Line', **kwargs):
        dir = get_3d_vector(direction)
        pt = get_3d_vector(point)
        pt_0 = pt - 100.0 * dir
        pt_1 = pt + 100.0 * dir
        super().__init__(pt_0, pt_1, width=width, bias=bias, name=name, **kwargs)
