import math
from .curves import BaseCurve, DEFAULT_LINE_WIDTH
from .bezier import BezierSpline
from .points import Empty, Point
from .attachments import BaseAttachment
from apeiron.globals.general import Vector, Euler, UnitZ, create_mesh, add_object, disable_print, enable_print

DEFAULT_FILLET_FACTOR = 0.0


class Joint(BaseAttachment, BaseCurve):
    """
    Todo
    """

    # class Type(Enum):
    #     MITER = 1
    #     ROUND = 2
    #     BEVEL = 3
    #     POINT = 4

    def __init__(self, curve_1: BaseCurve, curve_2: BaseCurve, width=DEFAULT_LINE_WIDTH, bias=0.0,
                 fillet_factor=DEFAULT_FILLET_FACTOR, num_subdiv=0, name='Joint'):
        """
        4--------3---------2
        |                  |
        |                  |
        |                  |
        5        .0        8 ------- C1
        |                  |
        |                  |
        |                  |
        6--------7---------1
                 |
                 |
                 |C0

        Parameters:
        curve_1
        curve_2
        width
        bias
        fillet_factor
        num_subdiv
        name
        """

        self.path = BezierSpline([(0, 0, 0)] * 3)

        self._offset_distance = 0.0
        assert fillet_factor >= 0.0
        if fillet_factor > 0.0:
            assert num_subdiv == 1
        self._fillet_factor = fillet_factor
        self._num_subdiv = num_subdiv

        super().__init__(name=name, connections=[
            curve_1, curve_2], width=width, bias=bias)

        self._update_geometry()
        self.add_object(self.path)

    def set_width(self, width: float):
        self.width = width
        self._update_geometry()
        return self

    def set_bias(self, bias: float):
        self.bias = bias
        self._update_geometry()
        return self

    def point(self, t: float) -> Vector:
        return self.path.point(t)

    def tangent(self, t: float, normalise=False) -> Vector:
        return self.path.tangent(t, normalise)

    def normal(self, t: float, normalise=False) -> Vector:
        return self.path.normal(t, normalise)

    def length(self, u: float = 1.0) -> float:
        return self.path.length(u)

    def offset_distance(self):
        return self._offset_distance

    def _update_geometry(self):
        curve_0 = self.connections[0]
        curve_1 = self.connections[1]

        p0 = curve_0.point(1)  # End of curve 1
        p1 = curve_1.point(0)  # Start of curve 2
        assert math.isclose(
            0, (p0 - p1).magnitude), "The curves must coincide at the joint."

        t0 = curve_0.tangent(1, normalise=True)
        t1 = curve_1.tangent(0, normalise=True)

        sgn = 1 if t0.cross(t1).dot(UnitZ) < 0 else -1
        n1 = sgn * UnitZ.cross(t0)
        n2 = sgn * UnitZ.cross(t1)
        n3 = -(n1 + n2)
        denom = abs(n3.dot(n1))
        n3 /= denom
        # if not math.isclose(denom, 0):
        #     n3 /= denom
        # else:
        #     print('p0:', p0)
        #     print('p0:', p0)

        w = self.width
        b = self.bias
        hw = 0.5 * w
        w0 = 0.5 * (b + 1) * w
        w1 = w - w0

        # Swap if CCW turn
        if sgn < 0:
            w0, w1 = w1, w0

        p1 = p0 + w0 * n3
        p3 = p0 + w1 * n2
        p5 = p0 + w1 * n1
        p2 = p1 + w * n2
        p6 = p1 + w * n1
        p4 = p1 - w * n3

        if math.isclose(denom, 0):
            print()
            print('p0:', p0)
            print('p1:', p1)
            print('p2:', p2)
            print('p6:', p6)

        self._offset_distance = abs((p2 - p3).magnitude)
        if self._num_subdiv == 0:  # Miter
            verts = [p1, p2, p4, p6]
            faces = [[0, 1, 2], [0, 2, 3]]
        elif self._num_subdiv == 1:  # Bevel
            # Need to recompute p3 and p5 based on the fillet factor.
            f = self._fillet_factor
            scal = (1 - f) * p4
            p3 = f * p2 + scal
            p5 = f * p6 + scal

            verts = [p1, p2, p3, p5, p6]
            faces = [[0, 1, 2], [0, 2, 3], [0, 3, 4]]
        else:  # Round
            n_subdiv = self._num_subdiv
            angle = n1.angle(n2)
            delta = angle / n_subdiv
            sgn = 1 if n1.cross(n2).dot(UnitZ) > 0 else -1
            eul = Euler((0.0, 0.0, sgn * delta), 'XYZ')
            n = n1.copy()

            verts = [p1, p2, p3, p5, p6]
            init = len(verts)
            faces = [[0, 1, 2], [0, 3, 4], [0, 2, 5],
                     [0, init + n_subdiv - 2, 3]]

            arc_points = []
            for i in range(n_subdiv - 1):
                n.rotate(eul)
                p = p0 + w1 * n
                arc_points.append(p)
                if i < n_subdiv - 2:
                    faces.append([0, init + i, init + i + 1])

            verts.extend(reversed(arc_points))

        # Create/update mesh
        if self.bl_obj is not None:
            self.bl_obj.data.clear_geometry()
            self.bl_obj.data.from_pydata(verts, [], faces)

            curve_0.update_param_1()
            curve_1.update_param_0()
        else:
            mesh = create_mesh('', verts=verts, faces=faces)
            self.bl_obj = add_object('', mesh)

            curve_0.set_attachment_1(self)
            curve_1.set_attachment_0(self)

        # Construct joint path
        p7 = p1 + hw * n1
        p8 = p1 + hw * n2
        pts = self.path._get_spline_points()
        pts[0].co = p7
        pts[1].co = p0
        pts[2].co = p8
        sp = self.path
        sp.set_both_handle_types(1, 'Vector')
        sp.set_width(w/50)
        sp.hide()

    def _set_param(self, param: float, end_index: int):
        pass

    def _update_attachment(self, end_index: int):
        pass
