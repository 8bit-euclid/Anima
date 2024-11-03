from .bezier import BezierCurve


class Segment(BezierCurve):
    def __init__(self, name='Line'):
        super().__init__(name)


class Ray(Segment):
    def __init__(self, name='Line'):
        super().__init__(name)


class Line(Segment):
    def __init__(self, name='Line'):
        super().__init__(name)
