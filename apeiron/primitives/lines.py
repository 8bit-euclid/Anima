from apeiron.globals.general import get_3d_vector
from .curves import DEFAULT_LINE_WIDTH
from .bezier import BezierCurve


class Segment(BezierCurve):
    def __init__(self, point_0, point_1, name='Segment', width=DEFAULT_LINE_WIDTH, bias=0.0):
        super().__init__(point_0, point_1, name, width, bias)
        self.set_resolution(1)

        # Disable redundant methods in parent class.
        self.set_handle_0 = None
        self.set_handle_1 = None


class Ray(Segment):
    def __init__(self, point, direction, name='Ray', width=DEFAULT_LINE_WIDTH, bias=0.0):
        pt_0 = get_3d_vector(point)
        pt_1 = pt_0 + 100.0 * get_3d_vector(direction)
        super().__init__(pt_0, pt_1, name, width, bias)


class Line(Segment):
    def __init__(self, point, direction, name='Line', width=DEFAULT_LINE_WIDTH, bias=0.0):
        dir = get_3d_vector(direction)
        pt = get_3d_vector(point)
        pt_0 = pt - 100.0 * dir
        pt_1 = pt + 100.0 * dir
        super().__init__(pt_0, pt_1, name, width, bias)
