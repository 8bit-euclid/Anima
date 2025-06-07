import math
import bisect
from enum import Enum

from .curves import Curve, DEFAULT_LINE_WIDTH
from .bezier import BezierSpline
from .points import Point
from .attachments import Attachment
from anima.primitives.mesh import Mesh
from anima.globals.general import Vector, Euler, UnitZ, are_vectors_close

DEFAULT_FILLET_FACTOR = 0.0
DEFAULT_RADIUS_FACTOR = 0.5
DEFAULT_NUM_SUBDIV = 15


class Joint(Attachment, Curve, Mesh):
    """
    Todo
    """

    class Type(Enum):
        MITER = 1
        ROUND = 2
        BEVEL = 3
        # POINT = 4

    def __init__(self, curve_1: Curve, curve_2: Curve, width: float = DEFAULT_LINE_WIDTH,
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

        # Set the joint path.
        path = BezierSpline([(0, 0, 0)] * 3)
        path.set_both_handle_types(1, 'Vector')
        path.set_width(width/50)
        path.hide()
        self._path = path

        # Now that the path is set, we can initialise super().
        super().__init__(connections=[curve_1, curve_2],
                         width=width, bias=bias, name=name)

        assert 0 <= fillet_factor <= 1, 'Currently, only a fillet factor in [0, 1] is supported.'
        self._fillet_factor = fillet_factor
        self._num_subdiv = num_subdiv
        self._vertices = []
        self._faces = []
        self._vertex_angles = []
        self._offset_distance = 0.0
        self._orientation = 1  # 1 if CW turn, else -1

        # Set the joint type
        self._type = None
        if self._num_subdiv == 0:
            self._type = Joint.Type.MITER
        elif self._num_subdiv == 1:
            self._type = Joint.Type.BEVEL
        else:
            self._type = Joint.Type.ROUND
        self._initialised = False

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

    # Private methods -------------------------------------------------------------------------------------- #

    def _update_geometry(self):
        p0, c, r, p1, p4, n1, n2, _ = self._compute_frame_info()

        # Compute remaining mesh vertices
        w = self._width
        p2 = p1 + w * n2
        p3 = c + r * n2
        p5 = c + r * n1
        p6 = p1 + w * n1

        # Update offset distance.
        _, w1 = self._compute_widths()
        p3_ = p0 + w1 * n2
        self._offset_distance = (p2 - p3_).magnitude

        # Create the vertex list for the different joint types.
        self._vertices = []
        verts = self._vertices
        type = self._type
        sgn = self._orientation
        if type == Joint.Type.MITER:
            verts.extend([p1, p2, p4, p6])
        elif type == Joint.Type.BEVEL:
            # Need to recompute p3 and p5 based on the fillet factor.
            f = self._fillet_factor
            scal = (1 - f) * p4
            p3 = f * p2 + scal
            p5 = f * p6 + scal

            verts.extend([p1, p2, p3, p5, p6])
        elif type == Joint.Type.ROUND:
            n_subdiv = self._num_subdiv
            angle = n1.angle(n2)
            delta = angle / n_subdiv
            eul = Euler((0.0, 0.0, sgn * delta), 'XYZ')
            v = n2.copy()

            verts.extend([p1, p2, p3])
            for i in range(n_subdiv - 1):
                v.rotate(eul)
                p = c + r * v
                verts.append(p)
            verts.extend([p5, p6])
        else:
            raise Exception(f'Unsupported joint type: {type}')

        # If necessary, reverse to maintain positive orientation.
        if sgn < 0:
            verts[1:] = reversed(verts[1:])

        # Compute vertex angles w.r.t. (verts[1] - p1)
        num_angles = len(verts) - 1
        self._vertex_angles = [0] * num_angles
        angles = self._vertex_angles
        ref = verts[1] - p1
        for i in range(1, num_angles):
            angles[i] = ref.angle(verts[i + 1] - p1)

        assert all(angles[i] <= angles[i+1] for i in range(len(angles) - 1))

        # Create mesh faces
        self._faces = []
        faces = self._faces
        for i in range(len(verts) - 2):
            faces.append([0, i + 1, i + 2])

        # Update/create mesh
        curve_0 = self.connections[0]
        curve_1 = self.connections[1]
        if self._initialised:
            self.update_mesh(verts, faces)
            curve_0._update_param_1()
            curve_1._update_param_0()
        else:
            self.set_mesh(verts, faces)
            curve_0.set_attachment_1(self)
            curve_1.set_attachment_0(self)
            self._initialised = True

        # Update joint path
        hw = 0.5 * w
        p7 = p1 + hw * n1
        p8 = p1 + hw * n2
        self._update_path([p7, p0, p8])

        # self.update_param_0()
        # self.update_param_1()

    def _compute_frame_info(self):
        curve_0 = self.connections[0]
        curve_1 = self.connections[1]

        p0 = curve_0.point(1)  # End of curve 1
        assert are_vectors_close(p0, curve_1.point(0)), \
            f"The curves must coincide at the joint. {p0} --- {(p0 - curve_1.point(0)).magnitude:.3e}"

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

        # Store orientation.
        self._orientation = sgn

        # Compute points 1 and 4.
        w0, w1 = self._compute_widths()
        w = self._width
        p1 = p0 + w0 * n3
        p4 = p1 - w * n3

        # Now compute the centre based on the bias and fillet factor.
        f = self._fillet_factor
        r = min(f*w, w1)
        c = p4 + r * n3

        return p0, c, r, p1, p4, n1, n2, n3

    def _compute_widths(self):
        w = self._width
        b = self._bias
        w0 = 0.5 * (b + 1) * w
        w1 = w - w0
        if self._orientation < 0:  # Swap if CCW turn
            w0, w1 = w1, w0
        return w0, w1

    def _update_path(self, points):
        path = self._path
        pts = path._spline_points()
        pts[0].co = points[0]
        pts[1].co = points[1]
        pts[2].co = points[2]
        path._update_length()

    def _set_param(self, param: float, end_idx: int):
        super()._set_param(param, end_idx)

        # Compute attachment offset and terminate curve accordingly.
        sgn = self._orientation
        if end_idx == 0:
            self._param_1 = 1.0
            # param_offs = self._compute_offset_param(param)
            cw_turn = sgn < 0
        else:
            self._param_0 = 0.0
            # param_offs = self._compute_offset_param(param)
            cw_turn = sgn > 0

        type = self._type
        if type not in [Joint.Type.MITER, Joint.Type.BEVEL, Joint.Type.ROUND]:
            raise Exception(f'Unsupported joint type: {type}')

        verts_init = self._vertices
        faces_init = self._faces

        p1 = verts_init[0]  # Assumed to be the first entry
        p2 = verts_init[1]
        pt = self.point(param)
        dir = pt - p1

        a = dir.angle(p2 - p1)
        angles = self._vertex_angles
        angl_idx_1 = bisect.bisect_left(angles, a)

        if angl_idx_1 == 0:
            verts = verts_init if cw_turn else []
            faces = faces_init if cw_turn else []
        elif angl_idx_1 == len(angles):
            verts = [] if cw_turn else verts_init
            faces = [] if cw_turn else faces_init
        else:
            angl_idx_0 = angl_idx_1 - 1
            a0 = angles[angl_idx_0]
            a1 = angles[angl_idx_1]

            offs = 1
            vert_idx_0 = angl_idx_0 + offs
            vert_idx_1 = angl_idx_1 + offs
            v0 = verts_init[vert_idx_0]
            v1 = verts_init[vert_idx_1]

            denom = a1 - a0
            pt = v0 if math.isclose(denom, 0) \
                else v0.lerp(v1, (a - a0)/denom)

            verts = [p1, pt] + verts_init[vert_idx_1:] if cw_turn \
                else verts_init[:vert_idx_1] + [pt]
            faces = faces_init[:len(verts) - 2]

        # Update/create mesh
        self.update_mesh(verts, faces)

    def _update_attachment(self, end_index: int):
        pass


class MiterJoint(Joint):
    def __init__(self, curve_1, curve_2, width=DEFAULT_LINE_WIDTH, bias=0, name='MiterJoint'):
        super().__init__(curve_1, curve_2,
                         width=width,
                         bias=bias,
                         name=name)


class BevelJoint(Joint):
    def __init__(self, curve_1, curve_2, width=DEFAULT_LINE_WIDTH, bias=0,
                 fillet_factor=DEFAULT_FILLET_FACTOR, name='BevelJoint'):
        super().__init__(curve_1, curve_2,
                         width=width,
                         bias=bias,
                         fillet_factor=fillet_factor,
                         num_subdiv=1,
                         name=name)


class RoundJoint(Joint):
    def __init__(self, curve_1, curve_2, width=DEFAULT_LINE_WIDTH, bias=0,
                 radius_factor=DEFAULT_RADIUS_FACTOR, num_subdiv=DEFAULT_NUM_SUBDIV, name='RoundJoint'):
        super().__init__(curve_1, curve_2,
                         width=width,
                         bias=bias,
                         fillet_factor=radius_factor,
                         num_subdiv=num_subdiv,
                         name=name)
