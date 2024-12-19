import bpy
import math
from .object import CustomObject
from .curves import BaseCurve, DEFAULT_LINE_WIDTH
from .bezier import BezierSpline
from .points import Empty, Point
from .attachments import BaseAttachment
from apeiron.globals.general import Vector, Euler, UnitZ, add_cuboid, make_active, extrude_active_obj, SMALL_OFFSET

DEFAULT_FILLET_FACTOR = 0.0
DEFAULT_NUM_SUBDIV = 10


class Joint(BaseAttachment, BaseCurve):
    """
    Todo
    """

    # class Type(Enum):
    #     MITER = 1
    #     ROUND = 2
    #     BEVEL = 3
    #     POINT = 4

    def __init__(self, curve_1: BaseCurve, curve_2: BaseCurve, width: float = DEFAULT_LINE_WIDTH,
                 bias: float = 0.0, fillet_factor: float = DEFAULT_FILLET_FACTOR, num_subdiv: int = 0,
                 name: str = 'Joint'):
        """
        4------3------2
        |             |
        |             |
        5      .0     8 -----> C1
        |             |
        |             |
        6------7------1
               ^
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

        path = BezierSpline([(0, 0, 0)] * 3)
        path.set_both_handle_types(1, 'Vector')
        path.set_width(width/50)
        path.hide()
        self._path = path

        super().__init__(connections=[curve_1, curve_2],
                         width=width, bias=bias, name=name)

        assert fillet_factor >= 0.0
        if fillet_factor > 0.0:
            assert num_subdiv == 1
        self._fillet_factor = fillet_factor
        self._num_subdiv = num_subdiv
        self._vertices = []
        self._offset_distance = 0.0

        self._update_geometry()

    def set_width(self, width: float):
        self._width = width
        self._update_geometry()
        return self

    def set_bias(self, bias: float):
        self._bias = bias
        self._update_geometry()
        return self

    def point(self, t: float) -> Vector:
        return self._path.point(t)

    def tangent(self, t: float, normalise=False) -> Vector:
        return self._path.tangent(t, normalise)

    def normal(self, t: float, normalise=False) -> Vector:
        return self._path.normal(t, normalise)

    def length(self, u: float = 1.0) -> float:
        return self._path.length(u)

    def offset_distance(self):
        return self._offset_distance

    def _update_geometry(self):
        p0, n1, n2, n3, sgn = self._compute_frame()
        w0, w1 = self._compute_widths(sgn)

        # Compute mesh vertices
        w = self._width
        p1 = p0 + w0 * n3
        p3 = p0 + w1 * n2
        p5 = p0 + w1 * n1
        p2 = p1 + w * n2
        p6 = p1 + w * n1
        p4 = p1 - w * n3

        # Update offset distance.
        self._offset_distance = abs((p2 - p3).magnitude)

        # Create the vertex list for the different joint types.
        self._vertices = []
        verts = self._vertices
        if self._num_subdiv == 0:  # Miter
            verts.extend([p1, p2, p4, p6])
        elif self._num_subdiv == 1:  # Bevel
            # Need to recompute p3 and p5 based on the fillet factor.
            f = self._fillet_factor
            scal = (1 - f) * p4
            p3 = f * p2 + scal
            p5 = f * p6 + scal

            verts.extend([p1, p2, p3, p5, p6])
        else:  # Round
            n_subdiv = self._num_subdiv
            angle = n1.angle(n2)
            delta = angle / n_subdiv
            eul = Euler((0.0, 0.0, sgn * delta), 'XYZ')
            v = n2.copy()

            verts.extend([p1, p2, p3])
            for i in range(n_subdiv - 1):
                v.rotate(eul)
                p = p0 + w1 * v
                verts.append(p)
            verts.extend([p5, p6])

        # If necessary, reverse to maintain positive orientation.
        if sgn < 0:
            verts[1:] = reversed(verts[1:])

        # Create mesh faces
        faces = []
        for i in range(len(verts) - 2):
            faces.append([0, i + 1, i + 2])

        # Update/create mesh
        curve_0 = self.connections[0]
        curve_1 = self.connections[1]
        if self.object is not None:
            self.update_mesh(verts, faces)
            curve_0.update_param_1()
            curve_1.update_param_0()
        else:
            self.set_mesh(verts, faces)
            curve_0.set_attachment_1(self)
            curve_1.set_attachment_0(self)

        # Update joint path
        hw = 0.5 * w
        p7 = p1 + hw * n1
        p8 = p1 + hw * n2
        self._update_path([p7, p0, p8])

    def _compute_frame(self):
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
        if not math.isclose(denom, 0):
            n3 /= denom
        else:
            self._offset_distance = 0.0

        return p0, n1, n2, n3, sgn

    def _compute_widths(self, sgn: int):
        w = self._width
        b = self._bias
        w0 = 0.5 * (b + 1) * w
        w1 = w - w0
        if sgn < 0:  # Swap if CCW turn
            w0, w1 = w1, w0
        return w0, w1

    def _update_path(self, points):
        path = self._path
        pts = path._get_spline_points()
        pts[0].co = points[0]
        pts[1].co = points[1]
        pts[2].co = points[2]
        path._update_length()

    def _set_param(self, param: float, end_index: int):
        # Compute attachment offset and terminate curve accordingly.
        if end_index == 0:
            self._param_1 = 1.0
            param_offs = self._compute_offset_param_0(param)
        else:
            self._param_0 = 0.0
            param_offs = self._compute_offset_param_1(param)

        super()._set_param(param, end_index)

    def _update_attachment(self, end_index: int):
        pass


class MiterJoint(Joint):
    def __init__(self, curve_1, curve_2, width=DEFAULT_LINE_WIDTH, bias=0, name='MiterJoint'):
        super().__init__(curve_1, curve_2,
                         width=width,
                         bias=bias,
                         name=name)


class BevelJoint(Joint):
    def __init__(self, curve_1, curve_2, width=DEFAULT_LINE_WIDTH, bias=0, fillet_factor=0.5,
                 name='BevelJoint'):
        super().__init__(curve_1, curve_2,
                         width=width,
                         bias=bias,
                         fillet_factor=fillet_factor,
                         num_subdiv=1,
                         name=name)


class RoundJoint(Joint):
    def __init__(self, curve_1, curve_2, width=DEFAULT_LINE_WIDTH, bias=0, radius=None,
                 num_subdiv=DEFAULT_NUM_SUBDIV, name='RoundJoint'):
        super().__init__(curve_1, curve_2,
                         width=width,
                         bias=bias,
                         num_subdiv=num_subdiv,
                         name=name)
