from .curves import DEFAULT_LINE_WIDTH
from .bezier_curve import BezierCurve
from anima.globals.general import Vector, make_3d_vector


class Segment(BezierCurve):
    def __init__(self, point_0, point_1, width=DEFAULT_LINE_WIDTH, bias=0.0, name='Segment', **kwargs):
        super().__init__(point_0, point_1, width=width, bias=bias, name=name,
                         num_lookup_pts=2, **kwargs)
        # Place handles at 1/3rd and 2/3rd of the way between the points.
        # This makes the Bezier parameter equivalent to the length fraction parameter.
        p0 = Vector(point_0)
        p1 = Vector(point_1)
        vect = (1/3) * (p1 - p0)
        self.handle_0 = vect
        self.handle_1 = -vect


class Ray(Segment):
    def __init__(self, point, direction, width=DEFAULT_LINE_WIDTH, bias=0.0, name='Ray', **kwargs):
        pt_0 = make_3d_vector(point)
        pt_1 = pt_0 + 100.0 * make_3d_vector(direction)
        super().__init__(pt_0, pt_1, width=width, bias=bias, name=name, **kwargs)


class Line(Segment):
    def __init__(self, point, direction, width=DEFAULT_LINE_WIDTH, bias=0.0, name='Line', **kwargs):
        dir = make_3d_vector(direction)
        pt = make_3d_vector(point)
        pt_0 = pt - 100.0 * dir
        pt_1 = pt + 100.0 * dir
        super().__init__(pt_0, pt_1, width=width, bias=bias, name=name, **kwargs)
